import csv
import json
from google.cloud import storage, pubsub_v1

PROJECT_ID = "iteng-itsystems"
PUBSUB_TOPIC = "topico-wow"

storage_client = storage.Client()
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)

def distribuir_analise(event, context):
    """
    Função gatilho do Cloud Storage que lê um arquivo CSV e publica
    cada linha em um tópico do Pub/Sub.
    """
    bucket_name = event['bucket']
    file_name = event['name']
    
    print(f"Processando arquivo: {file_name} do bucket: {bucket_name}.")

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    
    try:
        # Faz o download do arquivo como texto para processamento em memória
        blob_stream = blob.download_as_text(encoding='utf-8').splitlines()
    except Exception as e:
        print(f"Erro ao baixar ou decodificar o arquivo {file_name}: {e}")
        return

    # Lê o arquivo CSV linha por linha
    csv_reader = csv.DictReader(blob_stream)
    
    count = 0
    for row in csv_reader:
        # Garante que a coluna 'ordered_messages' existe e não está vazia
        if 'ordered_messages' in row and row['ordered_messages']:
            message_payload = {
                "id": f"{file_name}-{count}",
                "ordered_messages": row['ordered_messages']
            }
            
            # Converte o payload para bytes e publica no Pub/Sub
            message_bytes = json.dumps(message_payload).encode('utf-8')
            publisher.publish(topic_path, data=message_bytes)
            count += 1
        
    print(f"{count} mensagens publicadas para o arquivo {file_name}.")