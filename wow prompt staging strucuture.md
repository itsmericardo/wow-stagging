---

### **Documentação Técnica: WOW Analyzer**

Versão: 2.2 (Projeto Pausado)

Data: 24 de Julho de 2025

Autor: Ricardo Santos, assistido por Claude

#### **1. Visão Geral**

O sistema **WOW Analyzer** é uma aplicação web serverless projetada para analisar arquivos CSV contendo interações de atendimento ao cliente. Utiliza IA Generativa do Google (Gemini) para classificar cada interação e salva os resultados de forma estruturada para análise posterior.

**Status Atual:** Projeto pausado com duas implementações prontas para deploy manual.

#### **2. Arquitetura Atual**

O projeto possui duas implementações distintas:

### **2.1 Implementação Principal: wow-parser (Frontend Integrado)**

**Serviços GCP Utilizados:**
* **Cloud Functions (Gen 2):** Frontend e backend integrados
* **Cloud Storage:** Bucket `iteng-entrada-analise` para entrada e saída
* **Vertex AI (Gemini 2.5 Flash Lite):** Análise e classificação das interações

**URL de Acesso:** https://southamerica-east1-iteng-itsystems.cloudfunctions.net/wow-parser

**Características:**
- Interface web completa integrada
- Processamento síncrono em memória
- Preview das primeiras 50 linhas
- Estatísticas em tempo real
- Download direto do arquivo processado
- Autenticação configurada (IAP)

### **2.2 Implementação Alternativa: funcao-processadora (Deploy Manual)**

**Preparada para:**
* **Cloud Run Functions** ou **Cloud Functions**
* **Trigger Manual** ou **Bucket Trigger**
* **Deploy via Console GCP**

**Características:**
- Código simplificado e autocontido
- HTML integrado (sem dependências externas)
- CORS configurado para acesso público
- Gemini 1.5 Flash (mais estável)
- Pronto para configuração manual

#### **3. Estrutura de Arquivos**

```
wow-stagging/
├── wow-parser/                    # Implementação principal (funcionando)
│   ├── main.py                   # Backend + Frontend integrado
│   ├── requirements.txt          # Dependências completas
│   └── templates/
│       └── upload.html           # Interface web
├── funcao-processadora/          # Implementação alternativa (pronta)
│   ├── main.py                  # Código autocontido para deploy manual
│   └── requirements.txt         # Dependências essenciais
├── README.md                    # Documentação do projeto
├── learning.md                  # Aprendizados e lições
└── wow prompt staging strucuture.md  # Esta documentação
```

#### **4. Status dos Componentes**

| Componente | Status | Observações |
|------------|--------|-------------|
| **Frontend** | ✅ Funcionando | Interface completa com preview, stats e download |
| **Backend** | ✅ Funcionando | Processamento CSV, upload, storage |
| **Autenticação** | ✅ Configurada | IAP ativo, não permite acesso público |
| **Processamento IA** | ⚠️ **Pendente** | Gemini retorna "Erro no processamento" |
| **Deploy Manual** | ✅ Pronto | Código preparado para Cloud Run Functions |

#### **5. Problema Identificado**

**Gemini API:** Todas as chamadas para o Vertex AI retornam "Erro no processamento da IA", resultando em:
- Estatísticas zeradas (0 Normal, 0 Bom, 0 WoW)
- Todas as linhas marcadas como "Erro"
- Arquivo processado é criado mas sem classificações válidas

**Possíveis Causas:**
- Quotas do Vertex AI
- Permissões insuficientes
- Configuração de região (us-central1 vs southamerica-east1)
- Modelo Gemini indisponível ou deprecated

#### **6. Configuração e Deploy**

### **6.1 Deploy da Função Principal (Atual)**
```bash
cd wow-parser
gcloud functions deploy wow-parser \
  --project iteng-itsystems \
  --region southamerica-east1 \
  --runtime python311 \
  --source . \
  --entry-point upload_service \
  --trigger-http \
  --timeout=540 --memory=2Gi \
  --set-env-vars BUCKET_NAME=iteng-entrada-analise
```

### **6.2 Deploy Manual Alternativo (Pronto)**
1. **Console GCP** → Cloud Functions ou Cloud Run Functions
2. **Código:** `funcao-processadora/main.py`
3. **Dependências:** `funcao-processadora/requirements.txt`
4. **Entry Point:** `upload_service`
5. **Trigger:** HTTP (allow unauthenticated)
6. **Environment:** `BUCKET_NAME=iteng-entrada-analise`

#### **7. Próximos Passos (Quando Retomar)**

### **Prioridade 1: Resolver Problema do Gemini**
- [ ] Verificar quotas do Vertex AI no projeto
- [ ] Testar diferentes modelos (gemini-1.5-flash, gemini-pro)
- [ ] Verificar permissões da service account
- [ ] Considerar migrar para us-central1
- [ ] Abrir chamado no suporte GCP se necessário

### **Prioridade 2: Otimizações**
- [ ] Implementar retry automático para falhas de IA
- [ ] Adicionar logs mais detalhados
- [ ] Criar fallback para processamento sem IA
- [ ] Implementar processamento em lotes para arquivos grandes

### **Prioridade 3: Funcionalidades**
- [ ] Autenticação via service account para acesso público
- [ ] Interface para visualização de histórico
- [ ] Exportação de dashboards e gráficos
- [ ] Filtros e busca na interface

#### **8. Limitações Conhecidas**

- **Política Organizacional:** Não permite `--allow-unauthenticated` em Cloud Functions
- **Processamento IA:** Falha sistemática nas chamadas do Gemini
- **Timeout:** Limitado a 540s para arquivos muito grandes
- **Memória:** 2GB pode ser insuficiente para CSVs > 100MB

#### **9. Arquivos de Backup**

- `GUIA_COMPLETO_IMPLEMENTACAO_backup.md` - Guia completo (copiado)
- `learning_backup.md` - Aprendizados (copiado)

---

**Projeto pausado em 24/07/2025**  
**Próxima ação:** Resolver problema de processamento Gemini/Vertex AI

