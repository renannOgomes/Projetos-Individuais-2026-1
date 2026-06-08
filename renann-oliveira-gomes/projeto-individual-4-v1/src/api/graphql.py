"""API GraphQL com Strawberry."""

import logging
from typing import Optional, List

import strawberry

from src.catalog.database import get_db_session
from src.catalog.repository import CatalogRepository

logger = logging.getLogger(__name__)


@strawberry.type
class MetricaGraphQL:
    """Métrica em schema GraphQL."""

    chave: str
    valor_absoluto: Optional[str]
    unidade: str
    pagina: Optional[int]
    confianca: float
    fonte_pdf: str
    secao: Optional[str] = None
    tipo_extracao: str = "texto_livre"


@strawberry.type
class ConjunturaGraphQL:
    """Resultado de conjuntura."""

    empresa: str
    ano: int
    trimestre: int
    metricas: List[MetricaGraphQL]
    total_metricas: int


@strawberry.type
class DocumentoGraphQL:
    """Documento ingerido."""

    id: str
    empresa: str
    ano: int
    trimestre: int
    source_url: str
    status: str


@strawberry.type
class Query:
    """Root query do schema GraphQL."""

    @strawberry.field
    async def conjuntura(
        self,
        empresa: str,
        ano: int,
        trimestre: int,
    ) -> Optional[ConjunturaGraphQL]:
        """Busca métricas de conjuntura por empresa e período."""
        try:
            session = get_db_session()
            repo = CatalogRepository(session)
            
            # TODO: Query no PostgreSQL
            # metrics = repo.get_metrics_by_empresa_trimestre(empresa, ano, trimestre)
            
            return ConjunturaGraphQL(
                empresa=empresa,
                ano=ano,
                trimestre=trimestre,
                metricas=[],
                total_metricas=0,
            )
        except Exception as e:
            logger.error(f"Erro ao buscar conjuntura: {e}")
            return None

    @strawberry.field
    async def metricas_por_fonte(
        self,
        documento_id: str,
    ) -> List[MetricaGraphQL]:
        """Rastreia todas as métricas de um documento (linhagem)."""
        try:
            session = get_db_session()
            repo = CatalogRepository(session)
            
            # TODO: Query de linhagem
            # metrics = repo.get_metrics_by_document(documento_id)
            
            return []
        except Exception as e:
            logger.error(f"Erro ao buscar linhagem: {e}")
            return []

    @strawberry.field
    async def documentos(
        self,
        empresa: Optional[str] = None,
        ano: Optional[int] = None,
    ) -> List[DocumentoGraphQL]:
        """Lista documentos ingeridos com filtros opcionais."""
        try:
            session = get_db_session()
            repo = CatalogRepository(session)
            
            # TODO: Query de documentos
            # docs = repo.get_documents(empresa=empresa, ano=ano)
            
            return []
        except Exception as e:
            logger.error(f"Erro ao listar documentos: {e}")
            return []


schema = strawberry.Schema(query=Query)
