import datetime
import json
from google.cloud import storage
import functions_framework

# --- Variáveis de Configuração ---
# O bucket para onde os arquivos serão enviados pelo frontend.
BUCKET_NAME = "iteng-entrada-analise" 

@functions_framework.http
def gerar_url_assinada(request):
    """
    Função HTTP que gera uma URL assinada (signed URL) para permitir
    o upload de um arquivo diretamente para o Cloud Storage.
    """
    # --- Tratamento de CORS (Cross-Origin Resource Sharing) ---
    # Essencial para permitir que o frontend (rodando em um navegador)
    # chame esta função de backend.
    headers = {
        'Access-Control-Allow-Origin': '*', # Para produção, restrinja para o domínio do seu frontend
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Max-Age': '3600'
    }

    # Responde à requisição "pre-flight" OPTIONS do navegador
    if request.method == 'OPTIONS':
        return ('', 204, headers)

    # --- Lógica Principal ---
    if request.method == 'POST':
        request_json = request.get_json(silent=True)
        if not request_json or 'fileName' not in request_json:
            error_message = 'Requisição JSON inválida. O campo "fileName" é obrigatório.'
            return (error_message, 400, headers)
        
        file_name = request_json['fileName']
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_name)

        try:
            # Gera a URL assinada que permite um upload (PUT) e expira em 15 minutos
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(minutes=15),
                method="PUT",
                content_type="text/csv"  # O tipo de conteúdo que o frontend deve enviar
            )
            
            # Retorna a URL em um corpo JSON para o frontend
            response_data = json.dumps({"url": signed_url})
            headers['Content-Type'] = 'application/json'
            return (response_data, 200, headers)

        except Exception as e:
            error_message = f"Erro interno ao gerar URL assinada: {e}"
            headers['Content-Type'] = 'text/plain'
            return (error_message, 500, headers)
            
    else:
        # Rejeita qualquer método que não seja POST ou OPTIONS
        error_message = 'Método não permitido. Use POST.'
        headers['Content-Type'] = 'text/plain'
        return (error_message, 405, headers) 