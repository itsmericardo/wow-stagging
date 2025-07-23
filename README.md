# 🟣 WoW Analyzer - Sistema Identificador de WOW's

![WoW Analyzer Banner](https://nubank.com.br/favicon.ico)

Bem-vindo ao **WoW Analyzer**! Este projeto é a sua central de análise inteligente de conversas de atendimento, usando IA de última geração para identificar momentos "WoW" que encantam clientes. Tudo com a cara (e o roxo) do Nubank! 💜

---

## 🚀 O que é?

O WoW Analyzer é uma solução serverless, divertida e poderosa, que:
- Recebe arquivos CSV de conversas de atendimento
- Usa IA (Gemini) para classificar cada interação como **Normal**, **Bom** ou **WoW**
- Gera uma planilha processada com raciocínio e classificação
- Mostra um preview visual e permite download direto do resultado
- Tudo isso com uma interface moderna, responsiva e roxa!

---

## 🧩 Como funciona?

1. **Upload do CSV**
   - Arraste ou selecione seu arquivo na interface web
2. **Processamento IA**
   - O backend chama o modelo Gemini para cada linha
   - Adiciona duas colunas: `raciocinio` e `classificacao_final`
3. **Visualização**
   - Preview das primeiras 50 linhas na tela
   - Estatísticas de Normal/Bom/WoW
   - Cronômetro de processamento em tempo real
4. **Download**
   - Baixe a planilha processada direto do bucket (link público)

---

## 🏗️ Arquitetura

```
Usuário 👩‍💻
   │
   ▼
Frontend (HTML+JS)  ←→  Cloud Function (Python)
   │                        │
   ▼                        ▼
Google Cloud Storage   Vertex AI (Gemini)
```

- **Frontend:** HTML5, CSS3, JS (puro, sem frameworks!)
- **Backend:** Python 3.11, Google Cloud Functions (Gen2)
- **IA:** Gemini 1.5 Flash (Vertex AI)
- **Storage:** Google Cloud Storage (bucket público para download)

---

## 🛠️ Como rodar/testar

### 1. **Pré-requisitos**
- Conta GCP com billing ativo
- Permissões para Cloud Functions, Vertex AI, Storage
- Python 3.11, gcloud CLI

### 2. **Deploy**

```bash
gcloud functions deploy wow-parser \
  --project iteng-itsystems \
  --region southamerica-east1 \
  --runtime python311 \
  --source wow-parser/ \
  --entry-point upload_service \
  --trigger-http \
  --set-env-vars BUCKET_NAME=iteng-entrada-analise \
  --timeout=540 --memory=2Gi
```

### 3. **Acesse a interface**
Abra no navegador:
```
https://southamerica-east1-iteng-itsystems.cloudfunctions.net/wow-parser
```

### 4. **Faça upload e divirta-se!**
- Veja o cronômetro rodando
- Preview das classificações
- Baixe o resultado e compartilhe com o time

---

## 🧙‍♂️ Dicas mágicas
- Use arquivos CSV com a coluna `ordered_messages`
- O sistema aceita até 100MB por arquivo
- O preview mostra só as primeiras 50 linhas (mas o download é completo!)
- O botão "Limpar" cancela tudo e reseta a interface
- O sistema é roxo porque... Nubank! 💜

---

## 🤖 Tecnologias usadas
- [Google Cloud Functions](https://cloud.google.com/functions)
- [Vertex AI Gemini](https://cloud.google.com/vertex-ai/docs/generative-ai/learn/model-versions)
- [Google Cloud Storage](https://cloud.google.com/storage)
- [Python 3.11](https://www.python.org/)
- [HTML5/CSS3/JS](https://developer.mozilla.org/)

---

## 🦄 Contribua!
Pull requests são bem-vindos! Sinta-se livre para sugerir melhorias, novas features ou só deixar um elogio roxo.

---

## 📜 Licença
MIT. Use, compartilhe, melhore e espalhe o WoW!

---

> "O melhor atendimento é aquele que surpreende. O melhor código é aquele que encanta!" – Equipe WoW Analyzer
