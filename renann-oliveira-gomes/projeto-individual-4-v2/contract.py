from pydantic import BaseModel, Field
from typing import Optional

class ConjunturaHabitacional(BaseModel):
    """Contrato semântico para a extração dos dados dos relatórios de Relações com Investidores."""
    empresa: str = Field(description="Nome da construtora ou incorporadora.")
    ano: int = Field(description="Ano de referência do relatório.")
    trimestre: int = Field(description="Trimestre de referência do relatório (1, 2, 3 ou 4).")
    
    # Métricas Operacionais - Valores Absolutos
    unidades_vendidas: Optional[int] = Field(None, description="Número absoluto de unidades vendidas no trimestre.")
    vgv_lancado: Optional[float] = Field(None, description="Valor Geral de Vendas (VGV) lançado em milhões de Reais (R$).")
    vgv_vendido: Optional[float] = Field(None, description="Valor Geral de Vendas (VGV) vendido em milhões de Reais (R$).")
    vso: Optional[float] = Field(None, description="Velocidade sobre a Oferta (VSO) consolidada em porcentagem.")
    estoque_unidades: Optional[int] = Field(None, description="Número bruto total de unidades em estoque.")
    
    # Métricas Financeiras
    receita_liquida: Optional[float] = Field(None, description="Receita líquida total registrada em milhões de Reais (R$).")