"""Main API com FastAPI + GraphQL."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse

from src.api.graphql import schema
from src.catalog.database import init_db
from src.catalog.repository import CatalogRepository
from src.config import get_settings
from src.ingestion.downloader import PDFDownloader
from src.ingestion.webhook import WebhookIngester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia lifecycle da aplicação."""
    # Startup
    logger.info("Inicializando banco de dados...")
    init_db()
    logger.info("API iniciada ✓")
    
    yield
    
    # Shutdown
    logger.info("Encerrando API...")


app = FastAPI(
    title="UDA Pipeline — Setor Habitacional",
    description="RAG + Multi-Agent Extraction + GraphQL API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "llm_provider": settings.llm_provider,
    }


@app.post("/graphql")
async def graphql_endpoint(data: dict):
    """
    Endpoint GraphQL.
    
    POST /graphql
    {
      "query": "{ conjuntura(empresa: \"MRV\", ano: 2025, trimestre: 3) { empresa } }"
    }
    """
    try:
        query = data.get("query")
        variables = data.get("variables", {})
        
        if not query:
            raise ValueError("Query não fornecida")
        
        result = await schema.execute(query, variable_values=variables)
        
        if result.errors:
            return JSONResponse(
                status_code=400,
                content={"errors": [str(e) for e in result.errors]}
            )
        
        return JSONResponse({"data": result.data})
    
    except Exception as e:
        logger.error(f"Erro em GraphQL: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/webhooks/ingest")
async def webhook_ingest(
    payload: dict,
    x_webhook_signature: str = Header(None),
):
    """
    Webhook para ingestão de novos PDFs das Centrais de Resultados.
    
    POST /webhooks/ingest
    X-Webhook-Signature: sha256=abc123...
    {
      "source": "MRV",
      "pdf_url": "https://...",
      "published_at": "2025-10-15T14:32:00Z"
    }
    """
    try:
        if not x_webhook_signature:
            raise ValueError("Assinatura não fornecida")
        
        # Inicializar ingestor
        webhook = WebhookIngester(settings.webhook_secret)
        
        # Inicializar downloader
        from src.catalog.database import get_db_session
        session = get_db_session()
        repo = CatalogRepository(session)
        downloader = PDFDownloader(repo, settings.pdf_storage_path)
        
        # Processar webhook
        result = await webhook.process_webhook(
            payload,
            x_webhook_signature,
            downloader,
        )
        
        session.close()
        return result
    
    except ValueError as e:
        logger.error(f"Erro na validação do webhook: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint com documentação."""
    return {
        "name": "UDA Pipeline — Setor Habitacional",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "graphql": "POST /graphql",
            "webhooks": {
                "ingest": "POST /webhooks/ingest",
            },
            "docs": {
                "swagger": "/docs",
                "redoc": "/redoc",
            },
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
