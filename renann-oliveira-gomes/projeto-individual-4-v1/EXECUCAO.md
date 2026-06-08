# Guia de Execução e Testes

## Como Rodar o Projeto

### 1. Setup Inicial

```bash
# Clonar/entrar no diretório
cd c:\dev-renann-win\UnB\GCES\renann\Projetos-Individuais-2026-1\renann-oliveira-gomes\projeto-individual-4

# Criar .env
cp .env.example .env

# Editar .env com sua chave Gemini
# GEMINI_API_KEY=sua-chave-aqui
```

### 2. Docker Compose (Recomendado)

```bash
# Build e start
docker-compose up --build -d

# Verificar saúde
docker-compose ps

# Ver logs
docker-compose logs -f api
docker-compose logs -f scheduler

# Parar
docker-compose down
```

### 3. Testar Health Check

```bash
curl http://localhost:8000/health

# Esperado:
# {"status":"healthy","version":"1.0.0","llm_provider":"gemini"}
```

### 4. Testar GraphQL

```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ documentos { id empresa } }"
  }'
```

### 5. Testar CLI (dentro do container)

```bash
# Extração com fixture
docker-compose exec api python -m src.cli \
  tests/fixtures/exemplo.pdf \
  --empresa Conjuntura \
  --ano 2025 \
  --trimestre 3

# Scan (uma vez)
docker-compose exec api python -m src.cli scan --once

# Scheduler (daemon)
docker-compose exec scheduler python -m src.cli scan --daemon
```

### 6. Testes

```bash
# Rodar todos os testes
docker-compose exec api pytest tests/ -v

# Rodar apenas testes de extração
docker-compose exec api pytest tests/test_extraction.py -v

# Rodar com coverage
docker-compose exec api pytest tests/ --cov=src --cov-report=html
```

## Modo Desenvolvimento (sem Docker)

```bash
# Python 3.11+
python -m venv .venv
.venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Inicializar banco (PostgreSQL deve estar rodando)
python -c "from src.catalog.database import init_db; init_db()"

# Rodar API
uvicorn src.api.main:app --reload

# Rodar scheduler
python -m src.ingestion.scheduler

# CLI
python -m src.cli tests/fixtures/exemplo.pdf --empresa MRV
```

## Endpoints Disponíveis

### REST/HTTP

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Info API |
| GET | `/health` | Health check |
| POST | `/graphql` | GraphQL API |
| POST | `/webhooks/ingest` | Webhook ingestão |

### GraphQL Queries

```graphql
# Conjuntura por período
query {
  conjuntura(empresa: "MRV", ano: 2025, trimestre: 3) {
    empresa
    ano
    trimestre
    metricas {
      chave
      valorAbsoluto
      unidade
      confianca
      fontePDF
    }
    totalMetricas
  }
}

# Linhagem de um documento
query {
  metricasPorFonte(documentoId: "uuid") {
    chave
    valorAbsoluto
    fontePDF
    pagina
  }
}

# Listar documentos
query {
  documentos(empresa: "MRV", ano: 2025) {
    id
    empresa
    ano
    trimestre
    sourceUrl
    status
  }
}
```

## Troubleshooting

### Erro: "could not translate host name postgres"

```bash
# Usar localhost em vez de postgres
DATABASE_URL=postgresql://uda_user:uda_password@localhost:5433/uda_rag
```

### Erro: "No module named 'sentence_transformers'"

```bash
pip install sentence-transformers
```

### Erro: "GEMINI_API_KEY not set"

```bash
# Editar .env ou setar variável
export GEMINI_API_KEY=sua-chave
```

### PostgreSQL não inicia

```bash
# Remover volume antigo
docker volume rm projeto-individual-4_postgres_data

# Rebuild
docker-compose down -v
docker-compose up --build -d
```

## Workflow Típico

1. **Ingestão**: Webhook ou scheduler descobre novo PDF
2. **Download**: PDFDownloader faz download + hash + dedup
3. **Processamento**: 
   - Parser extrai texto
   - RAGChunker divide em chunks semânticos
   - MultiAgentExtractor: classifica → extrai → merge
4. **Persistência**: Métricas + linhagem em PostgreSQL
5. **Consulta**: GraphQL expõe dados

## Performance Tips

- Embeddings: use GPU se disponível (`device="cuda"`)
- Chunking: aumentar `FULL_SCAN_PAGE_THRESHOLD` para documentos curtos
- LLM: usar modelo mais rápido para latência reduzida
- Vector Search: manter índice pgvector otimizado

## Próximos Passos

- [ ] Implementar Vision fallback (slides)
- [ ] GraphQL Subscriptions (notificações)
- [ ] Fine-tuning dos agentes
- [ ] Dashboard UI
- [ ] Análise temporal
