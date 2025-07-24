import json
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.cloud import storage
import csv
import io
import uuid
from flask import request, jsonify
from werkzeug.utils import secure_filename
import logging
import traceback

# Configurações
PROJECT_ID = "iteng-itsystems"
LOCATION = "us-central1"
BUCKET_NAME = "iteng-entrada-analise"

# Inicialização
vertexai.init(project=PROJECT_ID, location=LOCATION)
storage_client = storage.Client()
logger = logging.getLogger(__name__)

# Prompt para análise
PROMPT = """
Atue como um Analista de Qualidade (QA) de Atendimento ao Cliente, sênior e meticuloso.
Analise a interação e classifique em: Normal, Bom ou WoW.

Critérios:
- Normal: Interação rotineira, sem elementos especiais
- Bom: Demonstra eficiência, proatividade ou satisfação do cliente
- WoW: Conexão humana significativa, solução criativa, momentos de vida importantes

Formato de saída JSON:
{"raciocinio": "breve explicação", "classificacao_final": "Normal/Bom/WoW"}
"""

def analisar_interacao(texto):
    """Chama Gemini para análise."""
    try:
        model = GenerativeModel("gemini-1.5-flash", system_instruction=[PROMPT])
        response = model.generate_content([Part.from_text(f"Interação: {texto}")])
        
        # Tentar extrair JSON da resposta
        text = response.text.strip()
        if text.startswith('```json'):
            text = text.replace('```json', '').replace('```', '').strip()
        
        return json.loads(text)
    except Exception as e:
        logger.error(f"Erro Gemini: {e}")
        return {"raciocinio": "Erro na análise", "classificacao_final": "Erro"}

def upload_service(request):
    """Função principal para processamento de CSV."""
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    if request.method == 'OPTIONS':
        return ('', 204, headers)
    
    if request.method == 'GET':
        # Retorna a página HTML
        return """
<!DOCTYPE html>
<html>
<head>
    <title>WoW Analyzer</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
        .upload-area { border: 2px dashed #662D91; padding: 40px; text-align: center; border-radius: 10px; }
        .btn { background: #662D91; color: white; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; }
        .result { margin-top: 30px; padding: 20px; background: #f9f9f9; border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #662D91; color: white; }
    </style>
</head>
<body>
    <h1>🎯 WoW Analyzer</h1>
    <div class="upload-area">
        <form id="upload-form" enctype="multipart/form-data">
            <input type="file" id="csv-file" accept=".csv" required>
            <br><br>
            <button type="submit" class="btn">Processar CSV</button>
        </form>
    </div>
    <div id="result"></div>

    <script>
        document.getElementById('upload-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData();
            formData.append('file', document.getElementById('csv-file').files[0]);
            
            document.getElementById('result').innerHTML = '<p>Processando...</p>';
            
            try {
                const response = await fetch(window.location.href, {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    let html = '<div class="result"><h3>Processamento Concluído!</h3>';
                    html += `<p>Linhas processadas: ${result.statistics.total_rows}</p>`;
                    html += `<p>Normal: ${result.statistics.normal_count} | Bom: ${result.statistics.bom_count} | WoW: ${result.statistics.wow_count}</p>`;
                    html += `<a href="${result.download_url}" class="btn">Download do Resultado</a>`;
                    
                    if (result.preview_data) {
                        html += '<h4>Preview (primeiras 10 linhas):</h4><table>';
                        html += '<tr><th>ID</th><th>Mensagem</th><th>Raciocínio</th><th>Classificação</th></tr>';
                        
                        result.preview_data.slice(0, 10).forEach(row => {
                            html += `<tr>
                                <td>${row.id || row.chat_id || ''}</td>
                                <td>${(row.ordered_messages || '').substring(0, 100)}...</td>
                                <td>${row.raciocinio || ''}</td>
                                <td>${row.classificacao_final || ''}</td>
                            </tr>`;
                        });
                        html += '</table>';
                    }
                    html += '</div>';
                    document.getElementById('result').innerHTML = html;
                } else {
                    document.getElementById('result').innerHTML = '<p>Erro: ' + result.error + '</p>';
                }
            } catch (error) {
                document.getElementById('result').innerHTML = '<p>Erro: ' + error.message + '</p>';
            }
        });
    </script>
</body>
</html>
        """
    
    # Processamento POST
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400, headers
    
    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Arquivo deve ser CSV'}), 400, headers
    
    try:
        # Lê CSV
        csv_content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(csv_content))
        
        if 'ordered_messages' not in reader.fieldnames:
            return jsonify({'error': 'Coluna "ordered_messages" não encontrada'}), 400, headers
        
        # Processa linhas
        fieldnames = list(reader.fieldnames) + ['raciocinio', 'classificacao_final']
        output_rows = []
        stats = {'total_rows': 0, 'normal_count': 0, 'bom_count': 0, 'wow_count': 0}
        
        for row in reader:
            stats['total_rows'] += 1
            texto = row.get('ordered_messages', '').strip()
            
            if texto:
                resultado = analisar_interacao(texto)
                row['raciocinio'] = resultado.get('raciocinio', 'Erro')
                row['classificacao_final'] = resultado.get('classificacao_final', 'Erro')
                
                # Conta estatísticas
                if row['classificacao_final'].lower() == 'normal':
                    stats['normal_count'] += 1
                elif row['classificacao_final'].lower() == 'bom':
                    stats['bom_count'] += 1
                elif row['classificacao_final'].lower() == 'wow':
                    stats['wow_count'] += 1
            else:
                row['raciocinio'] = 'Sem texto'
                row['classificacao_final'] = 'N/A'
            
            output_rows.append(row)
        
        # Salva resultado
        output_csv = io.StringIO()
        writer = csv.DictWriter(output_csv, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)
        
        # Upload para bucket
        session_id = str(uuid.uuid4())[:8]
        filename = f"processado_{session_id}_{secure_filename(file.filename)}"
        
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(f"processados/{filename}")
        blob.upload_from_string(output_csv.getvalue(), content_type='text/csv')
        blob.make_public()
        
        return jsonify({
            'success': True,
            'download_url': blob.public_url,
            'preview_data': output_rows,
            'statistics': stats,
            'message': 'Processamento concluído!'
        }), 200, headers
        
    except Exception as e:
        logger.error(f"Erro: {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Erro no processamento: {str(e)}'}), 500, headers