# Contrato Semântico — Métricas Operacionais

## Schema Pydantic

```python
class MetricaOperacional(BaseModel):
    chave: MetricKey
    valor_absoluto: Optional[Decimal]
    unidade: MetricUnit
    pagina: Optional[int]
    secao: Optional[str]
    tipo_extracao: Literal["tabela", "texto_livre", "inferido"]
    confianca: float  # 0.0 a 1.0
    trecho_evidencia: Optional[str]
    chunk_id: Optional[str]
```

## Regras de Negócio

### 1. Valores Absolutos (Obrigatório)

- ✅ Aceitar: "12.340 unidades", "R$ 2.5 bi", "2.5B"
- ❌ Rejeitar: "+15% vs 3T24", "crescimento de 8%"
- ⚠️ Ambiguidade: "120" → null (sem unidade)

### 2. Valores Ausentes

```python
# Se métrica não aparece no documento:
valor_absoluto = None  # NUNCA inventar!
```

### 3. Normalização de Unidades

| Input | Normalizado | Conversão |
|-------|------------|-----------|
| "2.5 bilhões" | `2500000000` | R$ → mantém |
| "2,5 B" | `2500000000` | ✓ |
| "2500 mil" | `2500000` | ✓ |
| "2.5%" | `2.5` | percentual_absoluto |

### 4. Trimestre Válido

```python
@validator
def validate_trimestre(cls, v: int) -> int:
    assert v in (1, 2, 3, 4), "trimestre ∈ {1,2,3,4}"
    return v
```

## Exemplo de Resposta Válida

```json
{
  "empresa": "MRV",
  "ano": 2025,
  "trimestre": 3,
  "metricas": [
    {
      "chave": "unidades_vendidas",
      "valor_absoluto": "4230",
      "unidade": "unidades",
      "pagina": 5,
      "secao": "Resultados Operacionais",
      "tipo_extracao": "tabela",
      "confianca": 0.95,
      "trecho_evidencia": "Tabela: Vendas 3T25 = 4.230 un.",
      "chunk_id": "p5_s2"
    },
    {
      "chave": "vgv",
      "valor_absoluto": "2500000000",
      "unidade": "R$",
      "pagina": 5,
      "secao": "Resultados Operacionais",
      "tipo_extracao": "tabela",
      "confianca": 0.95,
      "trecho_evidencia": "VGV: R$ 2.5B",
      "chunk_id": "p5_s2"
    },
    {
      "chave": "margem_bruta",
      "valor_absoluto": null,
      "unidade": "percentual_absoluto",
      "pagina": null,
      "secao": null,
      "tipo_extracao": "inferido",
      "confianca": 0.0,
      "trecho_evidencia": null,
      "chunk_id": null
    }
  ]
}
```

## Prompts Anti-Alucinação

### Prompt do Agente 1 (Classificador)

```
Você é um classificador de estruturas de documentos.
Seu trabalho é APENAS identificar se o texto contém:
- Uma TABELA (linhas, colunas, alinhamento)
- TEXTO NARRATIVO (prosa contínua)
- Uma IMAGEM (menos de 50 caracteres)

Você NÃO deve extrair valores. Apenas classificar.

Responda com EXATAMENTE uma destas palavras:
"tabela"
"texto_livre"
"imagem"

Nada mais.

Texto:
{chunk_text}
```

### Prompt do Agente 2 (Extrator Tabular)

```
Você é um especialista em extração de dados de tabelas financeiras.
Sua tarefa é extrair VALORES BRUTOS de uma tabela, nada mais.

IMPORTANTE:
1. NUNCA invente valores
2. Se um campo da tabela estiver vazio, retorne null
3. Sempre normalize números: 2.5B = 2500000000
4. Ignore análises, comentários ou interpretações
5. Responda APENAS em JSON válido

Procure EXATAMENTE estas métricas (se existem na tabela):
- unidades_vendidas
- vgv
- vso
- estoque_unidades
- obras_andamento
- receita_liquida
- margem_bruta

Tabela:
{chunk_text}

Responda em JSON:
{
  "metricas": [
    {"chave": "...", "valor_absoluto": ..., "unidade": "...", "confianca": 0.95}
  ]
}
```

### Prompt do Agente 3 (Extrator Textual)

```
Você é um analista de dados do setor imobiliário.
Leia este texto narrativo e extraia métricas operacionais ABSOLUTAS.

REGRAS RIGOROSAS:
1. Valores ABSOLUTOS apenas. Ignore "+15% vs 3T24"
2. Se não encontrar valor, retorne null (NÃO invente)
3. Se ambiguidade (ex: "120"), retorne null
4. Sempre cite o trecho que prova o valor
5. Confiança textual: 0.7 (menos precisa que tabela)

Procure:
- Unidades vendidas
- VGV (Valor Geral de Vendas)
- VSO (Velocidade sobre Oferta) em %
- Estoque
- Obras em andamento
- Receita líquida
- Margem bruta

Texto:
{chunk_text}

Responda em JSON:
{
  "metricas": [
    {
      "chave": "...",
      "valor_absoluto": ...,
      "unidade": "...",
      "trecho_evidencia": "...",
      "confianca": 0.7
    }
  ]
}
```

## Validação Pydantic Pós-LLM

```python
@validator("valor_absoluto")
def validate_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
    if v is not None and v < 0:
        raise ValueError("Valores negativos não são permitidos")
    return v

@validator("confianca")
def validate_confidence(cls, v: float) -> float:
    assert 0.0 <= v <= 1.0, "Confiança deve estar em [0, 1]"
    return v
```

## Exemplo de Rejeição

```json
// INVÁLIDO: Inventou valor
{
  "chave": "unidades_vendidas",
  "valor_absoluto": 1000,
  "unidade": "unidades",
  "trecho_evidencia": null  // ❌ Sem evidência = suspeito
}

// VÁLIDO: Returnando null
{
  "chave": "unidades_vendidas",
  "valor_absoluto": null,
  "unidade": "unidades",
  "trecho_evidencia": null
}
```

