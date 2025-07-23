---

### **Documentação Técnica: WOW Analyzer**

Versão: 2.0

Data: 23 de Julho de 2025

Autor: Ricardo Santos, assistido por Gemini

#### **1. Visão Geral**

O sistema **WOW Analyzer** é uma aplicação web serverless projetada para analisar arquivos CSV contendo interações de atendimento ao cliente. Utiliza IA Generativa do Google (Gemini) para classificar cada interação e salva os resultados de forma estruturada para análise posterior.

A arquitetura é construída inteiramente sobre serviços gerenciados do Google Cloud Platform (GCP), garantindo alta escalabilidade, segurança e baixo custo operacional. O sistema é visual, divertido e inspirado na identidade Nubank.

#### **2. Arquitetura da Solução (Atual)**

O sistema é composto por uma única Cloud Function (wow-parser) que serve tanto o frontend quanto o backend, tornando o fluxo mais simples e direto.

**Serviços GCP Utilizados:**

* **Cloud Functions (Gen 2):** Toda a lógica computacional, frontend e backend.
* **Cloud Storage:** Armazenamento dos arquivos de entrada (uploads) e saída (resultados processados).
* **Vertex AI (Gemini 1.5 Flash):** Análise de sentimento/classificação das interações.

**Fluxo de Dados End-to-End:**

1. **Acesso e Upload:**
   * O usuário acessa a URL da aplicação e faz upload de um arquivo CSV via interface web.
   * O arquivo é enviado diretamente para a função wow-parser, que processa o conteúdo em memória.
2. **Processamento IA:**
   * A função processa cada linha do CSV, chama o Gemini para análise e adiciona as colunas `raciocinio` e `classificacao_final`.
   * Um preview das primeiras 50 linhas é retornado para exibição imediata na interface.
   * O arquivo completo processado é salvo no bucket do Cloud Storage e tornado público para download.
3. **Visualização e Download:**
   * O usuário visualiza estatísticas, preview e pode baixar o arquivo processado diretamente por um link público.
   * Um cronômetro em tempo real mostra a duração do processamento.

#### **3. Componentes Detalhados**

| Função         | wow-parser (única) |
| :-------------| :----------------- |
| **Responsabilidade** | Servir o frontend (HTML), receber uploads, processar CSV, chamar IA, salvar e disponibilizar resultado, exibir preview e estatísticas |
| **Gatilho**   | HTTP Trigger |
| **Código Fonte** | ./wow-parser/ |

#### **4. Acesso ao Código Fonte**

O código fonte está versionado neste repositório GitHub.

#### **5. Segurança e Permissões**

* O download do arquivo processado é público (link direto do bucket), facilitando o compartilhamento.
* O upload e processamento são feitos via interface autenticada (IAP pode ser ativado se desejado).
* O deploy não utiliza `--allow-unauthenticated` para upload/processamento, mas o download é público para facilitar o uso.

#### **6. Configuração e Deploy**

1. **Criar Infraestrutura:**
   * Criar o bucket de entrada/saída no Cloud Storage (ex: `iteng-entrada-analise`).
2. **Fazer o Deploy da Função:**
   * Executar:
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
3. **Acessar a Interface:**
   * URL: https://southamerica-east1-iteng-itsystems.cloudfunctions.net/wow-parser

#### **7. Experiência do Usuário**

* Interface moderna, responsiva e roxa (Nubank style)
* Upload com drag & drop
* Cronômetro de processamento em tempo real
* Preview das primeiras 50 linhas processadas
* Estatísticas de Normal/Bom/WoW
* Download público do arquivo completo processado
* Botão "Limpar" para resetar a interface

#### **8. Manutenção e Próximos Passos**

* **Limite de 100MB por arquivo** para garantir performance e evitar timeouts.
* **Logs detalhados** para debug e rastreabilidade.
* **Possível evolução:**
  - Paginação/scroll virtual para previews maiores
  - Filtros e busca na interface
  - Exportação de gráficos e dashboards
  - Integração com autenticação IAP para uploads restritos

---

