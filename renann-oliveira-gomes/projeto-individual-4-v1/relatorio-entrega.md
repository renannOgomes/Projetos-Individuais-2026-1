# Relatório de Entrega — Projeto Individual 4: Pipeline UDA (RAG Edition)

> **Aluno:** Renann Oliveira Gomes  
> **Disciplina:** GCES — Projeto Extra  
> **Data de Entrega:** 08/06/2026  

---

## 1. Resumo do Projeto

Este projeto implementa uma **arquitetura alternativa** para o Pipeline de Análise de Dados Não Estruturados (UDA) do setor habitacional, focando em:

1. **RAG (Retrieval-Augmented Generation)** com embeddings semânticos
2. **Multi-Agent Extraction** (classificação + extração especializada)
3. **GraphQL API** para queries semânticas
4. **Webhook Support** para ingestão reativa
5. **Vector Search** com PostgreSQL + pgvector

---

## 2. Diferenças Arquiteturais Principais

### Chunking
- **Original**: Keywords regex simples
- **RAG**: Embeddings (sentence-transformers) + vector index

### Extração
- **Original**: Um único LLM
- **Multi-Agent**: 4 agentes especializados (classificador, tabular, textual, merge)

### API
- **Original**: REST (FastAPI)
- **Nova**: GraphQL (Strawberry)

### Ingestão
- **Original**: APScheduler polling
- **Nova**: Webhook reativo + polling fallback

### Vector DB
- **Original**: Sem
- **Nova**: PostgreSQL + pgvector para semantic search

### Processamento
- **Original**: Celery + Redis
- **Nova**: AsyncIO nativo

---

## 3. Stack Tecnológico

| Componente | Tecnologia |
|------------|------------|
| Linguagem | Python 3.11 |
| API | Strawberry GraphQL |
| Banco | PostgreSQL 16 + pgvector |
| LLM | Google Gemini + Instructor |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| PDF | PyMuPDF |
| Async | asyncio + aiohttp |
| Orquestração | Docker Compose |

---

## 4. Camadas da Solução

### Camada 1: Ingestão (Dual-Mode)

**Modo Reativo (Webhook)**
- Endpoints `/webhooks/ingest` recebem notificações
- Assinatura HMAC validada
- Processamento imediato

**Modo Resiliente (Polling)**
- APScheduler fallback
- Scan diário às 06:00 BRT
- Idempotência via SHA-256

### Camada 2: Extração (Multi-Agent)

```
Agente 1: Classificador
  → Detecta: tabela vs. texto_livre vs. imagem
  
Agente 2: Extrator Tabular
  → OCR + parsing de linhas/colunas
  → Confiança: 0.95
  
Agente 3: Extrator Textual
  → NLP em prosa narrativa
  → Confiança: 0.70
  
Agente 4: Merge & Dedup
  → Consolida resultados
  → Valida contra contrato Pydantic
```

### Camada 3: Catálogo + Vector Search

**Modelos PostgreSQL:**
- `documents`: metadados e status
- `semantic_chunks`: chunks com embeddings (pgvector)
- `metric_values`: métricas com linhagem
- `ingest_events`: log de eventos

**Vector Search:**
- Modelo: `all-MiniLM-L6-v2` (384-dim)
- Index: IVFFlat para performance
- Caso de uso: Recuperar chunks similares por semântica

### Camada 4: API GraphQL

**Vantagens:**
- Queries customizáveis sem overfetching
- Introspection automática
- Aliases para múltiplas métricas
- Subscriptions para real-time (future)

**Exemplo Query:**
```graphql
{
  conjuntura(empresa: "MRV", ano: 2025, trimestre: 3) {
    empresa
    metricas {
      chave
      valorAbsoluto
      unidade
      confianca
      fontePDF
    }
  }
}
```

---

## 5. Decisões Técnicas

### Por que RAG + Embeddings?

- Semântica real: encontra "venda de unidades" mesmo sem palavra "vendas"
- Resiliência: adapta-se a variações de linguagem
- Ranking: prioriza chunks mais relevantes
- Performance: modelo `all-MiniLM` é leve e open-source

### Por que Multi-Agent?

- Tabelas precisam OCR + parsing estruturado
- Texto livre precisa NLP
- Imagens precisam vision
- One-size-fits-all não funciona

### Por que GraphQL?

- Queries semanticamente ricas
- Evita overfetching/underfetching
- Auto-documentation
- Preparado para subscriptions

### Por que Webhooks?

- Ingestão reativa vs. polling
- Mais responsivo (minutos vs. horas)
- Reduz carga em servidores RI
- Polling como fallback

---

## 6. Fluxo Completo

```
1. [Webhook / Scheduler] → PDF descoberto
2. [Downloader] → Baixa e armazena
3. [SHA-256] → Verifica dedup
4. [Parser] → PyMuPDF extrai texto
5. [RAGChunker] → Chunks + embeddings
6. [VectorDB] → Salva chunks com índice
7. [Agent1] → Classifica tipo
8. [Agent2/3] → Extrai conforme tipo
9. [Merge] → Deduplica e valida
10. [PostgreSQL] → Persiste
11. [GraphQL] → Expõe
```

---

## 7. Estrutura do Projeto

```
projeto-individual-4/
├── src/
│   ├── ingestion/       # Webhook + Scraper + Downloader
│   ├── extraction/      # Parser + RAGChunker + MultiAgent
│   ├── contracts/       # Pydantic schemas
│   ├── catalog/         # PostgreSQL + repository
│   ├── api/             # GraphQL API
│   ├── workers/         # Async tasks
│   ├── config.py        # Settings
│   └── cli.py           # CLI para testes
├── docs/
│   ├── arquitetura.md
│   ├── rag-strategy.md
│   ├── multi-agent-design.md
│   └── contrato-semantico.md
├── tests/
│   ├── conftest.py
│   └── test_extraction.py
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── README.md
```

---

## 8. Como Executar

```bash
# Setup
cd projeto-individual-4
cp .env.example .env
# Edite: GEMINI_API_KEY

# Docker
docker-compose up --build -d

# Health check
curl http://localhost:8000/health

# GraphQL
open http://localhost:8000/graphql

# CLI test
docker-compose exec api python -m src.cli \
  tests/fixtures/exemplo.pdf \
  --empresa "Conjuntura" --ano 2025 --trimestre 3
```

---

## 9. Documentação Detalhada

- [Arquitetura](docs/arquitetura.md) — Visão geral e fluxos
- [RAG Strategy](docs/rag-strategy.md) — Embeddings + vector search
- [Multi-Agent Design](docs/multi-agent-design.md) — 4 agentes especializados
- [Contrato Semântico](docs/contrato-semantico.md) — Regras de validação

---

## 10. Resiliência contra Variações de Layout

- ✅ **RAG**: Não depende de keywords fixas
- ✅ **Multi-Agent**: Classifica e processa conforme tipo (tabela vs. texto)
- ✅ **Contrato**: Pydantic blinda contra valores inválidos
- ✅ **Linhagem**: Cada métrica rastreada até seu chunk e PDF

---

## 11. Próximos Passos (Future Work)

1. **Vision Fallback**: GPT-4o para slides rasterizados
2. **Subscriptions GraphQL**: Notificações de novos documentos
3. **Fine-tuning**: Otimizar agentes para setor habitacional
4. **Análise Temporal**: Insights sobre tendências entre trimestres
5. **Dashboard**: UI para visualizar métricas e linhagem

---

