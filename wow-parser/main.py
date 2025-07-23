import datetime
import os
import json
import csv
import io
import tempfile
import uuid
import traceback
import logging
import time
import threading
from google.cloud import storage
import functions_framework
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from werkzeug.utils import secure_filename

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variáveis de Configuração
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'iteng-entrada-analise')
PROJECT_ID = "iteng-itsystems"
LOCATION = "us-central1"

# Cache global para progresso das sessões
progress_cache = {}

# Inicialização do Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

# --- Prompt para Análise ---
PROMPT = """
Atue como um Analista de Qualidade (QA) de Atendimento ao Cliente, sênior e meticuloso.
Seu objetivo é garantir a consistência e a excelência na avaliação de interações, aplicando os critérios definidos com rigor.
Tarefa Principal
    - Analise a Interação para Análise fornecida abaixo e classifique-a em UMA das três categorias a seguir: Normal, Bom ou WoW. Siga o processo de raciocínio e os critérios detalhados.
        Critérios de Classificação
        ## Categoria 1: Normal
            * A interação é puramente informativa ou rotineira.
            * Não há elementos pessoais ou emocionais significativos.
            * O agente segue o protocolo padrão sem personalização extra.
            * A resolução não envolve criatividade ou empatia além do esperado.
        ## Categoria 2: Bom
            * O serviço é eficiente e está dentro dos padrões de resolução.
            * O agente demonstra proatividade, clareza ou paciência notável.
            * O cliente expressa satisfação, feedback positivo ou sentimentos bons sobre o atendimento.
        ## Categoria 3: WoW
            * A interação se destaca por uma conexão humana significativa e única.
            * Contém elementos pessoais ou demonstração clara de empatia (ex: hobbies, celebrações, interesses em comum).
            * O agente fornece uma solução criativa ou personalizada que vai além do protocolo padrão, gerando surpresa positiva.
            * A resolução é inspiradora ou inesperada, resultando em uma experiência diferenciada.
            * Um momento de vida importante do cliente é mencionado e reconhecido na interação (ex: casamento, aniversário, nascimento de filho, gravidez, conquista pessoal, viagem, mudança de endereço, mudança de nome social, desenvolvimento profissional).

        ### Regra de Exclusão Crítica
            - Atenção: Interações com temas sensíveis (fraude, golpe, morte, deficiência, flerte) NUNCA devem ser classificadas como Bom ou WoW, mesmo que o atendimento tenha sido excelente. 
            - Nesses casos, a classificação final deve ser obrigatoriamente Normal.

        ### Processo de Raciocínio (Chain of Thought)
            - Antes de fornecer a classificação final, siga estes passos mentais:
            - Análise Inicial: Leia a interação e identifique o problema principal e o tom geral da conversa.
            - Verificação Sequencial:
            - A interação se enquadra em Normal? Se sim, sua análise pode parar aqui, a menos que haja algo excepcional.
            - Se não for Normal, ela atinge os critérios de Bom?
            - Se for Bom, verifique se existem elementos que a elevam para WoW.
            - Verificação Final (Obrigatória): A Regra de Exclusão Crítica se aplica a esta interação? Se sim, ignore as análises anteriores e classifique como Normal.
            - Justificativa: Formule uma breve justificativa para sua escolha com base nos critérios.
        
        Formato da Saída
        Sua resposta sera um objeto JSON contendo dois campos:
            1 - Raciocinio: Uma breve explicação (1-2 frases) de por que a interação recebeu tal classificação, baseada no seu processo de raciocínio.
            2 - Classificacao_final: A palavra final: Normal, Bom ou WoW.
"""

def analisar_interacao(texto_interacao: str) -> dict:
    """Chama o modelo Gemini para analisar o texto e retorna um dicionário."""
    try:
        # Usar o modelo correto disponível na região us-central1
        model = GenerativeModel("gemini-2.5-flash-lite", system_instruction=[PROMPT])
        response = model.generate_content(
            [Part.from_text(f"Interação para Análise: {texto_interacao}")],
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Erro ao analisar interação: {e}")
        return {"raciocinio": "Erro no processamento da IA", "classificacao_final": "Erro"}

def update_progress(session_id: str, current: int, total: int, status: str = "processing", extra_data: dict = None):
    """Atualiza o progresso de uma sessão no cache."""
    progress_data = {
        'current': current,
        'total': total,
        'percentage': round((current / total) * 100, 1) if total > 0 else 0,
        'status': status,
        'timestamp': time.time()
    }
    
    if extra_data:
        progress_data.update(extra_data)
    
    progress_cache[session_id] = progress_data
    logger.info(f"Progresso atualizado - Sessão: {session_id}, {current}/{total} ({progress_data['percentage']}%)")

def estimate_processing_time(file_size_mb: float) -> dict:
    """Estima o tempo de processamento baseado no tamanho do arquivo."""
    # Estimativas baseadas em benchmarks reais
    base_time_per_mb = 2.5  # segundos por MB para processamento de texto + IA
    overhead = 10  # segundos de overhead para setup
    
    estimated_seconds = (file_size_mb * base_time_per_mb) + overhead
    estimated_minutes = estimated_seconds / 60
    
    return {
        "seconds": int(estimated_seconds),
        "minutes": round(estimated_minutes, 1),
        "formatted": f"{int(estimated_minutes)}min {int(estimated_seconds % 60)}s" if estimated_minutes >= 1 else f"{int(estimated_seconds)}s"
    }

def make_blob_public(bucket_name: str, blob_path: str) -> str:
    """Torna o blob público e retorna a URL pública."""
    try:
        storage_client = get_storage_client()
        if not storage_client:
            logger.error("Storage client não disponível para tornar blob público")
            return f"https://storage.googleapis.com/{bucket_name}/{blob_path}"
            
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        # Tornar o blob público
        blob.make_public()
        
        # Retornar URL pública
        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_path}"
        logger.info(f"Blob tornado público: {public_url}")
        
        return public_url
    except Exception as e:
        logger.error(f"Erro ao tornar blob público: {e}")
        logger.error(traceback.format_exc())
        # Fallback: retornar URL direta mesmo sem permissão pública
        return f"https://storage.googleapis.com/{bucket_name}/{blob_path}"

def processar_csv_streaming(csv_content: str, session_id: str, max_preview_rows: int = 50) -> tuple:
    """Processa um CSV aplicando o prompt com updates de progresso em tempo real."""
    try:
        # Ler o CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        fieldnames = list(csv_reader.fieldnames) + ['raciocinio', 'classificacao_final']
        
        # Primeiro, contar total de linhas para progresso
        csv_reader_count = csv.DictReader(io.StringIO(csv_content))
        total_rows = sum(1 for row in csv_reader_count)
        logger.info(f"Total de linhas para processar: {total_rows}")
        
        # Inicializar progresso
        update_progress(session_id, 0, total_rows, "starting")
        
        # Criar CSV de saída
        output = io.StringIO()
        csv_writer = csv.DictWriter(output, fieldnames=fieldnames)
        csv_writer.writeheader()
        
        processed_count = 0
        preview_data = []
        
        # Determinar tamanho do chunk baseado no número total de linhas
        if total_rows <= 100:
            chunk_size = 5
        elif total_rows <= 500:
            chunk_size = 10
        elif total_rows <= 1000:
            chunk_size = 20
        else:
            chunk_size = 50
        
        # Resetar o reader
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        start_time = time.time()
        
        for row_index, row in enumerate(csv_reader, 1):
            # Verificar se existe a coluna 'ordered_messages'
            if 'ordered_messages' in row and row['ordered_messages']:
                resultado = analisar_interacao(row['ordered_messages'])
                row['raciocinio'] = resultado.get('raciocinio', 'Erro no processamento')
                row['classificacao_final'] = resultado.get('classificacao_final', 'Erro')
                processed_count += 1
            else:
                row['raciocinio'] = 'Sem mensagem para analisar'
                row['classificacao_final'] = 'N/A'
            
            csv_writer.writerow(row)
            
            # Guardar dados para preview (apenas primeiras linhas)
            if len(preview_data) < max_preview_rows:
                preview_data.append(dict(row))
            
            # Atualizar progresso em chunks ou ao finalizar
            if row_index % chunk_size == 0 or row_index == total_rows:
                elapsed_time = time.time() - start_time
                avg_time_per_row = elapsed_time / row_index if row_index > 0 else 0
                remaining_rows = total_rows - row_index
                estimated_remaining_time = remaining_rows * avg_time_per_row
                
                update_progress(
                    session_id, 
                    row_index, 
                    total_rows, 
                    "processing",
                    {
                        'processed_count': processed_count,
                        'elapsed_time': round(elapsed_time, 1),
                        'estimated_remaining': round(estimated_remaining_time, 1),
                        'avg_time_per_row': round(avg_time_per_row, 2)
                    }
                )
        
        # Calcular estatísticas finais
        stats = {
            'total_rows': total_rows,
            'processed_rows': processed_count,
            'normal_count': sum(1 for row in preview_data if row.get('classificacao_final') == 'Normal'),
            'bom_count': sum(1 for row in preview_data if row.get('classificacao_final') == 'Bom'),
            'wow_count': sum(1 for row in preview_data if row.get('classificacao_final') == 'WoW')
        }
        
        # Marcar como concluído
        update_progress(session_id, total_rows, total_rows, "completed", {
            'processed_count': processed_count,
            'total_time': round(time.time() - start_time, 1),
            'stats': stats
        })
        
        logger.info(f"Processamento concluído: {processed_count}/{total_rows} linhas analisadas")
        return output.getvalue(), preview_data, fieldnames, stats
        
    except Exception as e:
        logger.error(f"Erro ao processar CSV: {e}")
        update_progress(session_id, 0, 0, "error", {'error_message': str(e)})
        raise

def processar_csv_async(csv_content: str, session_id: str, filename: str):
    """Processa CSV de forma assíncrona em thread separada."""
    try:
        logger.info(f"Iniciando processamento assíncrono para sessão {session_id}")
        processed_csv, preview_data, column_names, stats = processar_csv_streaming(csv_content, session_id)
        
        logger.info(f"Processamento concluído, salvando no storage...")
        
        # Salvar o CSV processado no Storage
        processed_filename = f"processado_{filename}"
        blob_path = f"processados/{session_id}/{processed_filename}"
        
        storage_client = get_storage_client()
        if not storage_client:
            raise Exception("Falha ao obter cliente do Storage")
            
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(processed_csv, content_type='text/csv')
        logger.info(f"CSV processado salvo em: {blob_path}")
        
        # Tornar o arquivo público para download
        download_url = make_blob_public(BUCKET_NAME, blob_path)
        if not download_url:
            raise Exception("Falha ao tornar blob público")
            
        logger.info(f"Download URL criada: {download_url}")
        
        # Atualizar cache com dados finais
        logger.info(f"Atualizando cache final com resultados...")
        update_progress(session_id, stats['total_rows'], stats['total_rows'], "completed", {
            'download_url': download_url,
            'processed_filename': processed_filename,
            'preview_data': preview_data,
            'column_names': column_names,
            'statistics': stats,
            'total_time': 0  # Adicionar tempo total
        })
        
        logger.info(f"Processamento assíncrono concluído com sucesso para sessão {session_id}")
            
    except Exception as e:
        logger.error(f"Erro no processamento assíncrono: {e}")
        logger.error(traceback.format_exc())
        update_progress(session_id, 0, 0, "error", {'error_message': str(e), 'traceback': traceback.format_exc()})

# --- Funções Auxiliares (baseadas no código fornecido) ---

def get_storage_client():
    """Inicializa e retorna o cliente do Google Cloud Storage."""
    try:
        return storage.Client()
    except Exception as e:
        logger.error(f"Erro ao inicializar cliente do Storage: {e}")
        return None

def upload_to_storage(bucket_name, source_file_path, destination_blob_name):
    """Faz o upload de um arquivo local para o Cloud Storage."""
    storage_client = get_storage_client()
    if not storage_client:
        return False
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_path)
        logger.info(f"Arquivo {source_file_path} enviado para {destination_blob_name}")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar {source_file_path}: {e}")
        return False

# --- Função Principal da Cloud Function ---

@functions_framework.http
def upload_service(request):
    """
    Função HTTP unificada que atua como um serviço de backend e frontend.
    - Se a requisição for GET para a raiz ('/'), serve a página de upload.
    - Se a requisição for POST para '/upload', recebe arquivos e os salva no Storage.
    - Se a requisição for POST para '/process', processa um CSV com o prompt.
    """
    
    # Debug - imprimir informações da requisição
    print(f"Method: {request.method}")
    print(f"Path: {request.path}")
    print(f"URL: {request.url}")
    
    # --- Tratamento de CORS (Cross-Origin Resource Sharing) ---
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Max-Age': '3600'
    }

    if request.method == 'OPTIONS':
        return ('', 204, headers)

    # --- Roteamento da Requisição ---

    # Rota 1: Servir a página HTML do frontend
    if request.method == 'GET' and request.path == '/':
        try:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            file_path = os.path.join(dir_path, 'templates', 'upload.html')
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            headers['Content-Type'] = 'text/html'
            return (html_content, 200, headers)
        except FileNotFoundError:
            return ('Arquivo HTML não encontrado.', 404, headers)
        except Exception as e:
            return (f"Erro ao servir HTML: {e}", 500, headers)

    # Rota 2: Consultar progresso de uma sessão
    elif request.method == 'GET' and 'progress' in request.path:
        try:
            # Extrair session_id da URL (ex: /progress/session_id)
            path_parts = request.path.split('/')
            session_id = path_parts[-1] if len(path_parts) > 1 else None
            
            if not session_id:
                return (json.dumps({'success': False, 'message': 'Session ID não fornecido'}), 400, headers)
            
            progress_data = progress_cache.get(session_id)
            
            if not progress_data:
                return (json.dumps({'success': False, 'message': 'Sessão não encontrada'}), 404, headers)
            
            # Limpar dados antigos (> 1 hora)
            if time.time() - progress_data.get('timestamp', 0) > 3600:
                progress_cache.pop(session_id, None)
                return (json.dumps({'success': False, 'message': 'Sessão expirada'}), 410, headers)
            
            response_data = {
                'success': True,
                'session_id': session_id,
                'progress': progress_data
            }
            
            headers['Content-Type'] = 'application/json'
            return (json.dumps(response_data), 200, headers)
            
        except Exception as e:
            logger.error(f"Erro ao consultar progresso: {e}")
            return (json.dumps({'success': False, 'message': f'Erro interno: {e}'}), 500, headers)

    # Rota 3: Upload de arquivos
    elif request.method == 'POST' and (request.path == '/' or 'upload' in request.path):
        try:
            if 'files[]' not in request.files:
                return (json.dumps({'success': False, 'message': 'Nenhum arquivo selecionado'}), 400, headers)
            
            files = request.files.getlist('files[]')
            if not files or files[0].filename == '':
                return (json.dumps({'success': False, 'message': 'Nenhum arquivo selecionado'}), 400, headers)

            session_id = str(uuid.uuid4())
            processed_files = []
            
            # Use o diretório temporário do ambiente da Cloud Function
            with tempfile.TemporaryDirectory() as temp_dir:
                for file in files:
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        local_path = os.path.join(temp_dir, filename)
                        file.save(local_path)
                        
                        # Upload para o Cloud Storage
                        blob_path = f"uploads/{session_id}/{filename}"
                        if upload_to_storage(BUCKET_NAME, local_path, blob_path):
                            processed_files.append(filename)
                        else:
                            raise Exception(f"Falha no upload do arquivo {filename} para o Storage.")

            if not processed_files:
                return (json.dumps({'success': False, 'message': 'Nenhum arquivo válido processado'}), 400, headers)
            
            response_data = {
                'success': True,
                'session_id': session_id,
                'uploaded_files': processed_files,
                'message': 'Arquivos enviados com sucesso.'
            }
            headers['Content-Type'] = 'application/json'
            return (json.dumps(response_data), 200, headers)

        except Exception as e:
            logger.error(f"Erro durante o upload: {e}")
            logger.error(traceback.format_exc())
            return (json.dumps({'success': False, 'message': f'Erro durante processamento: {e}', 'traceback': traceback.format_exc()}), 500, headers)
    
    # Rota 4: Processar CSV com prompt
    elif request.method == 'POST' and 'process' in request.path:
        try:
            if 'file' not in request.files:
                return (json.dumps({'success': False, 'message': 'Nenhum arquivo CSV selecionado'}), 400, headers)
            
            file = request.files['file']
            if not file or file.filename == '':
                return (json.dumps({'success': False, 'message': 'Nenhum arquivo CSV selecionado'}), 400, headers)
            
            if not file.filename.lower().endswith('.csv'):
                return (json.dumps({'success': False, 'message': 'Apenas arquivos CSV são aceitos'}), 400, headers)

            session_id = str(uuid.uuid4())
            
            # Calcular tamanho do arquivo e estimar tempo
            file.seek(0, 2)  # Vai para o final do arquivo
            file_size_bytes = file.tell()
            file.seek(0)  # Volta para o início
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            # Verificar limite de tamanho (100MB)
            if file_size_mb > 100:
                return (json.dumps({'success': False, 'message': f'Arquivo muito grande ({file_size_mb:.1f}MB). Limite máximo: 100MB'}), 400, headers)
            
            time_estimate = estimate_processing_time(file_size_mb)
            logger.info(f"Arquivo: {file.filename}, Tamanho: {file_size_mb:.2f}MB, Tempo estimado: {time_estimate['formatted']}")
            
            # Ler o conteúdo do CSV
            csv_content = file.read().decode('utf-8')
            
            # Processar o CSV com o prompt DIRETAMENTE (sem thread)
            logger.info(f"Iniciando processamento do CSV: {file.filename}")
            processed_csv, preview_data, column_names, stats = processar_csv_streaming(csv_content, session_id)
            
            # Salvar o CSV processado no Storage
            processed_filename = f"processado_{file.filename}"
            blob_path = f"processados/{session_id}/{processed_filename}"
            
            storage_client = get_storage_client()
            if storage_client:
                bucket = storage_client.bucket(BUCKET_NAME)
                blob = bucket.blob(blob_path)
                blob.upload_from_string(processed_csv, content_type='text/csv')
                logger.info(f"CSV processado salvo em: {blob_path}")
                
                # Tornar o arquivo público para download
                download_url = make_blob_public(BUCKET_NAME, blob_path)
            
            response_data = {
                'success': True,
                'session_id': session_id,
                'original_filename': file.filename,
                'processed_filename': processed_filename,
                'download_url': download_url,
                'file_size_mb': round(file_size_mb, 2),
                'processing_time_estimate': time_estimate,
                'storage_path': f"gs://{BUCKET_NAME}/{blob_path}",
                'preview_data': preview_data,
                'column_names': column_names,
                'statistics': stats,
                'message': 'CSV processado com sucesso!'
            }
            headers['Content-Type'] = 'application/json'
            return (json.dumps(response_data), 200, headers)

        except Exception as e:
            logger.error(f"Erro durante processamento do CSV: {e}")
            logger.error(traceback.format_exc())
            return (json.dumps({'success': False, 'message': f'Erro durante processamento: {e}', 'traceback': traceback.format_exc()}), 500, headers)
            
    else:
        # Rota não encontrada
        return ('Rota não encontrada.', 404, headers)