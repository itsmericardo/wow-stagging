import base64
import json
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.cloud import storage

# --- Variáveis Finais e Corretas para seu Ambiente ---
PROJECT_ID = "iteng-itsystems"
LOCATION = "us-central1"
OUTPUT_BUCKET_NAME = "wow-datasets" 

# --- Inicialização dos Clientes ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
storage_client = storage.Client()

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
    model = GenerativeModel("gemini-1.0-pro", system_instruction=[PROMPT])
    response = model.generate_content(
        [Part.from_text(f"Interação para Análise: {texto_interacao}")],
        generation_config={"response_mime_type": "application/json"}
    )
    try:
        return json.loads(response.text)
    except Exception as e:
        print(f"Erro ao decodificar a resposta da IA: {e}")
        return {"raciocinio": "Erro no processamento da IA", "classificacao_final": "Erro"}

def processar_sentimento(event, context):
    """Função gatilho do Pub/Sub que salva o resultado no Cloud Storage."""
    if 'data' in event:
        message_data = base64.b64decode(event['data']).decode('utf-8')
        message_json = json.loads(message_data)
        
        texto_interacao = message_json.get("ordered_messages")
        message_id = message_json.get("id", context.event_id)

        if not texto_interacao:
            print("Erro: 'ordered_messages' não encontrado.")
            return

        resultado_analise = analisar_interacao(texto_interacao)
        
        source_file_prefix = message_id.split('-')[0]
        destination_blob_name = f"resultados/{source_file_prefix}/{message_id}.json"
        
        bucket = storage_client.bucket(OUTPUT_BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)
        
        blob.upload_from_string(
            json.dumps(resultado_analise, ensure_ascii=False, indent=2),
            content_type='application/json'
        )
        
        print(f"Resultado salvo em: gs://{OUTPUT_BUCKET_NAME}/{destination_blob_name}")