"""Contrato semântico para extração de métricas com multi-agent."""

from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

MetricKey = Literal[
    "unidades_vendidas",
    "vgv",
    "vso",
    "estoque_unidades",
    "obras_andamento",
    "receita_liquida",
    "margem_bruta",
]

MetricUnit = Literal["unidades", "R$", "milhoes_R$", "percentual_absoluto"]


class MetricaOperacional(BaseModel):
    """Métrica operacional extraída via multi-agent."""

    chave: MetricKey
    valor_absoluto: Optional[Decimal] = Field(
        default=None,
        description="Valor bruto; null se não encontrado",
    )
    unidade: MetricUnit
    pagina: Optional[int] = None
    secao: Optional[str] = None
    tipo_extracao: Literal["tabela", "texto_livre", "inferido"] = "texto_livre"
    confianca: float = Field(ge=0.0, le=1.0, default=0.8)
    trecho_evidencia: Optional[str] = Field(default=None, max_length=500)
    chunk_id: Optional[str] = None


class Extracao(BaseModel):
    """Resultado agregado de extração para um documento."""

    empresa: str
    ano: int
    trimestre: int = Field(ge=1, le=4)
    metricas: list[MetricaOperacional] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
