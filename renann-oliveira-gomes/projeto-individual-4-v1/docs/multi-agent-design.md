# Multi-Agent Extraction Design

## Motivação

Extrair métricas de documentos variados requer lidar com:
- **Tabelas estruturadas** (linhas/colunas com valores precisos)
- **Texto narrativo** (métricas dispersas em prosa)
- **Slides em imagens** (valores rasterizados sem OCR)

Uma estratégia one-size-fits-all não funciona. Múltiplos agentes especializados conseguem melhor acurácia.

## Arquitetura de Agentes

### Agente 1: Classificador (Graph Prompt)

```
Entrada: Chunk de texto
Decisão:
  - É TABELA? (linhas, colunas, alinhamento numérico)
  - É TEXTO LIVRE? (prosa com métricas dispersas)
  - É IMAGEM? (< 50 chars texto)

Saída: enum { "tabela", "texto_livre", "imagem" }
```

**Prompt:**
```
Você é um classificador de documentos financeiros. 
Analise este trecho e determine se contém:
- Uma TABELA estruturada com linhas/colunas
- TEXTO NARRATIVO com dados dispersos em prosa
- Uma IMAGEM (sem texto extraível)

Responda APENAS com um destes: "tabela" | "texto_livre" | "imagem"

Trecho:
{chunk_text}
```

### Agente 2: Extrator Tabular

Especializado em:
- Detecção de linhas/colunas
- Parsing numérico (tratamento de separadores: . vs ,)
- Alinhamento de headers

```python
async def extract_from_table(chunk: Chunk) -> list[MetricaOperacional]:
    # 1. Detecta estrutura (row, col)
    # 2. Identifica headers
    # 3. Para cada linha: extrai (métrica, valor)
    # 4. Valida contra contrato Pydantic
    # 5. Retorna com confianca=0.95 (tabelas são precisas)
```

**Prompt:**
```
Você é um especialista em extração de dados de TABELAS financeiras.
Analise esta tabela e extraia EXATAMENTE os valores numéricos.

Métricas buscadas:
- unidades_vendidas
- vgv (Valor Geral de Vendas)
- vso (Velocidade de Vendas sobre Oferta)
- estoque_unidades
- obras_andamento
- receita_liquida
- margem_bruta

Tabela:
{chunk_text}

Responda em JSON com lista de:
[
  {
    "chave": "vgv",
    "valor_absoluto": 2500000000,
    "unidade": "R$",
    "confianca": 0.95
  }
]
```

### Agente 3: Extrator Textual

Especializado em:
- NLP para encontrar métricas em prosa
- Extração de contexto (anterior/posterior)
- Detecção de negação ("não houve vendas")

```python
async def extract_from_text(chunk: Chunk) -> list[MetricaOperacional]:
    # 1. Tokeniza texto
    # 2. Busca padrões: "{número} {unidade} de {métrica}"
    # 3. Extrai contexto (janela de 50 chars antes/depois)
    # 4. Valida sem inventar valores
    # 5. Retorna com confianca=0.70 (texto é aproximado)
```

**Prompt:**
```
Você é um analista de dados de setor imobiliário.
Este trecho contém informações em texto narrativo sobre performance trimestral.

Extraia APENAS as métricas operacionais absolutas mencionadas:
- Unidades vendidas no período
- VGV (Valor Geral de Vendas)
- VSO (Velocidade de Vendas sobre Oferta) — em %
- Estoque de unidades
- Obras em andamento
- Receita líquida
- Margem bruta

IMPORTANTE:
- Nunca invente valores
- Se a métrica não aparecer, use null
- Ignore variações % de marketing ("+15% vs 3T24")
- Sempre cite o trecho textual que prova a métrica

Texto:
{chunk_text}

Responda em JSON:
{
  "metricas": [
    {
      "chave": "unidades_vendidas",
      "valor_absoluto": 4230,
      "unidade": "unidades",
      "trecho_evidencia": "No trimestre, as vendas totalizaram 4.230 unidades...",
      "confianca": 0.75
    }
  ]
}
```

### Agente 4: Merge & Dedup

Consolida resultados dos agentes anteriores:

```python
def merge_metrics(
    table_metrics: list[MetricaOperacional],
    text_metrics: list[MetricaOperacional],
) -> list[MetricaOperacional]:
    """
    Merge inteligente:
    1. Por chave métrica
    2. Prefere maior confianca
    3. Se igual, prefere com trecho_evidencia
    4. Se igual, prefere tabular (mais preciso)
    """
    merged = {}
    
    for metric in table_metrics + text_metrics:
        existing = merged.get(metric.chave)
        
        if existing is None:
            merged[metric.chave] = metric
        elif metric.confianca > existing.confianca:
            merged[metric.chave] = metric
        elif (metric.confianca == existing.confianca and 
              metric.tipo_extracao == "tabela"):
            merged[metric.chave] = metric
    
    return list(merged.values())
```

## Fluxo de Execução

```
Para cada Chunk:
    ↓
[Agente 1] → Classificação
    ↓
    ├─ "tabela" → [Agente 2] → Extração Tabular
    │
    ├─ "texto_livre" → [Agente 3] → Extração Textual
    │
    └─ "imagem" → [Vision Fallback] → GPT-4o
    ↓
[Agente 4] → Merge
    ↓
[Validação Pydantic] → ExtracaoConjuntura
    ↓
[Persistência] → PostgreSQL
```

## Resiliência e Fallback

Se Agente 2 (Tabular) falhar:
- Tenta Agente 3 (Textual) no mesmo chunk
- Se ambos falham: chunk é ignorado (não inventa)

Se todos agentes falham para um documento:
- Status = "processing" (não "failed")
- Retorna `Extracao` com `metricas=[]`
- Admin pode revisar logs

## Custos de Token

| Agente | Tokens Médios | Custo |
|--------|---------------|-------|
| Classificador | 100 | $$$ |
| Tabular | 500 | $$$ |
| Textual | 800 | $$$ |
| **Total/Doc** | ~2000 | ~$0.01 |

**Otimização:** Processa apenas top-K chunks mais relevantes (via vector search).

