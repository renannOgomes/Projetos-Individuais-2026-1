# RAG Strategy — Chunking com Embeddings

## Motivação

A estratégia original (keywords regex) tem limitações:
- Keywords podem não aparecer em variações semânticas
- Documentos com vocabulário atípico são perdidos
- Sem medida de relevância semântica

A abordagem RAG (Retrieval-Augmented Generation) resolve com:
- **Embedding**: cada chunk é vetorizado (384-dim, `all-MiniLM-L6-v2`)
- **Vector Index**: pgvector para recuperação semântica
- **Relevance Scoring**: similaridade cosseno para ranking

## Fluxo RAG

```
Documento PDF
    ↓
[Parser] → páginas com texto
    ↓
[Splitter] → chunks semânticos (~256 tokens cada)
    ↓
[Embeddings] → vetor 384-dim por chunk
    ↓
[pgvector Index] → IVFFlat para retrieval rápido
    ↓
[Semantic Search] → recupera top-K chunks relevantes
    ↓
[LLM Agent] → extrai métricas apenas dos chunks relevantes
```

## Implementação em `src/extraction/chunker.py`

```python
class RAGChunker:
    def chunk(self, doc_structure) -> list[Chunk]:
        # 1. Parse por quebras duplas (\n\n)
        # 2. Filtra seções muito curtas (< 10 chars)
        # 3. Classifica como "operacional" ou "texto"
        # 4. Computa embedding com SentenceTransformer
        # 5. Retorna chunks com embedding=None se modelo indisponível
```

## Vantagens

| Vantagem | Benefício |
|----------|-----------|
| **Semântica real** | Encontra trechos sobre "venda de unidades" mesmo sem keyword "vendas" |
| **Resiliência** | Adapta-se a variações de linguagem entre construtoras |
| **Ranking** | Prioriza chunks mais relevantes (economia de tokens) |
| **Debug** | Similarity score mostra por que um chunk foi selecionado |

## Desvantagens

| Desvantagem | Mitigação |
|------------|-----------|
| **Latência** | Embedding é rápido (< 100ms por documento) |
| **Memória** | Índice pgvector é compacto (~1MB/10k chunks) |
| **Custo modelo** | `all-MiniLM` é pequeno, open-source, sem API cost |

## Hiperparâmetros Ajustáveis

```python
# Em src/extraction/chunker.py
EMBEDDINGS_MODEL = "all-MiniLM-L6-v2"  # 384 dims
CHUNK_SIZE = 256  # tokens aprox
CHUNK_OVERLAP = 32  # tokens
RELEVANCE_THRESHOLD = 0.5  # similaridade mínima
TOP_K_CHUNKS = 10  # max chunks a processar
```

## Exemplo de Vector Search

```python
# Query: "unidades vendidas em 3T25"
query_embedding = embeddings.encode("unidades vendidas")  # [0.12, -0.45, ...]

# PostgreSQL
SELECT chunk_id, text, 
       1 - (embedding <=> query_embedding) as similarity
FROM semantic_chunks
WHERE 1 - (embedding <=> query_embedding) > 0.5
ORDER BY similarity DESC
LIMIT 10;
```

## Fallback sem Embeddings

Se `EMBEDDINGS_MODEL` não estiver disponível:
- `chunk.embedding = None`
- RAGChunker volta a usar heurística de keywords
- Sem penalidade de performance

