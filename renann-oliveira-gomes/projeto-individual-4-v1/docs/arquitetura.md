# Arquitetura — Pipeline UDA Habitacional (RAG + Multi-Agent)

## Visão Geral

Esta implementação se diferencia do projeto base através de:

1. **RAG (Retrieval-Augmented Generation)** com embeddings
2. **Multi-Agent Extraction** (classificação + extração especializada)
3. **GraphQL API** para queries semânticas
4. **Webhook support** para ingestão reativa
5. **Vector search** com PostgreSQL + pgvector

## Diagrama de Fluxo

```mermaid
flowchart TB
    subgraph ingest [Ingestão]
        Webhook["Webhook (Reativo)"]
        Scheduler["APScheduler (Fallback)"]
        Both["Scraper + Downloader"]
    end

    subgraph storage [Armazenamento]
        RawPDF["PDF Storage"]
        VectorDB["PostgreSQL + pgvector"]
    end

    subgraph extraction [Extração (Multi-Agent)]
        Parse["PyMuPDF Parser"]
        RAGChunk["RAG Chunker com Embeddings"]
        Agent1["Agente 1: Classificador<br/>(Tabela vs Texto)"]
        Agent2["Agente 2: Extrator Tabular"]
        Agent3["Agente 3: Extrator Textual"]
        Merge["Merge com Dedup"]
    end

    subgraph serve [Serviço]
        GraphQL["GraphQL API<br/>(Strawberry)"]
    end

    Webhook --> Both
    Scheduler --> Both
    Both --> RawPDF
    Both --> VectorDB
    RawPDF --> Parse
    Parse --> RAGChunk
    RAGChunk --> VectorDB
    RAGChunk --> Agent1
    Agent1 --> Agent2
    Agent1 --> Agent3
    Agent2 --> Merge
    Agent3 --> Merge
    Merge --> VectorDB
    VectorDB --> GraphQL
```

## Diferenças Arquiteturais

| Aspecto | Jefferson (Original) | Renann (Nova) |
|---------|----------------------|--------------|
| **Chunking** | Keywords regex | Embeddings semânticos + vector index |
| **Extração** | LLM único | 3 agentes especializados |
| **API** | REST FastAPI | GraphQL Strawberry |
| **Ingestão** | APScheduler apenas | Webhook + Polling |
| **Vector DB** | Não | PostgreSQL + pgvector |
| **Assincronismo** | Celery + Redis | AsyncIO nativo |

## Camada 1 — Ingestão (Dual-Mode)

### Modo Reativo (Webhook)
- Endpoints `/webhooks/ingest` recebem notificações dos portais RI
- Assinatura HMAC validada
- Processamento imediato

### Modo Resiliente (Polling)
- APScheduler fallback se webhooks falham
- Scan diário às 06:00 BRT
- Idempotência via SHA-256

## Camada 2 — Processamento UDA (Multi-Agent)

### Agente 1: Classificador
```
Entrada: Chunk de texto
Tarefa: Detectar se é tabela estruturada ou texto narrativo
Saída: "tabela" | "texto_livre"
```

### Agente 2: Extrator Tabular
```
Entrada: Chunk classificado como tabela
Tarefa: OCR + parsing de linhas/colunas
Saída: Lista de (métrica, valor, coluna_origem)
```

### Agente 3: Extrator Textual
```
Entrada: Chunk classificado como texto
Tarefa: NLP para encontrar métricas em prosa
Saída: Lista de (métrica, valor, trecho_evidência)
```

### Agente 4: Merge
```
Entrada: Resultados de Agent 2 + Agent 3
Tarefa: Deduplica e escolhe fonte com maior confiança
Saída: ExtracaoConjuntura validada
```

## Camada 3 — Vector Search + Catálogo

### Modelos PostgreSQL
- **`documents`**: metadados e status
- **`semantic_chunks`**: chunks com embeddings (pgvector)
- **`metric_values`**: métricas com linhagem
- **`ingest_events`**: log de eventos

### Vector Search
- Modelo: `all-MiniLM-L6-v2` (384-dim)
- Index: `ivfflat` para performance
- Caso de uso: "Encontre chunks similares a uma métrica X"

## Camada 4 — GraphQL API

### Vantagens sobre REST
- **Queries customizáveis** sem overfetching
- **Introspection** automática de schema
- **Aliases** para múltiplas métricas em um único request
- **Subscriptions** para mudanças em tempo real (future)

### Exemplo Query
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
      secao
    }
  }
}
```

## Fluxo Completo

```
1. [Webhook / Scheduler] → PDF descoberto
2. [Downloader] → Baixa e armazena em data/pdfs
3. [SHA-256] → Verifica dedup em catálogo
4. [Parser] → PyMuPDF extrai texto
5. [RAGChunker] → Divide em chunks + embeddings
6. [VectorDB] → Salva chunks com índice vetorial
7. [Agent1] → Classifica tipo de chunk
8. [Agent2/3] → Extrai conforme tipo
9. [Merge] → Deduplica e valida
10. [PostgreSQL] → Persiste métricas
11. [GraphQL] → Expõe via API
```

## Deduplicação Inteligente

- Ao encontrar mesma métrica em múltiplos chunks:
  - Prefere valor com maior `confianca`
  - Se confiança igual, prefere com `trecho_evidencia`
  - Se ambos iguais, mantém primeira ocorrência

## Exemplo de Linhagem

Cada métrica responde:
```json
{
  "chave": "vgv",
  "valor_absoluto": 2500000000,
  "unidade": "R$",
  "confianca": 0.95,
  "tipo_extracao": "tabela",
  "chunk_id": "p3_s1",
  "pagina": 3,
  "secao": "Resultados do Trimestre",
  "trecho_evidencia": "VGV (Valor Geral de Vendas): R$ 2.5 bilhões",
  "fonte_pdf": "s3://uda/MRV-3T25-20250430.pdf"
}
```

