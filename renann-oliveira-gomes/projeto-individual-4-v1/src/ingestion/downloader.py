"""Download e gerenciamento de PDFs com deduplicação."""

import hashlib
import logging
from pathlib import Path

import httpx

from src.catalog.repository import CatalogRepository

logger = logging.getLogger(__name__)


def compute_bytes_hash(data: bytes) -> str:
    """Calcula SHA-256 de um binário."""
    return hashlib.sha256(data).hexdigest()


async def download_pdf(url: str, dest_dir: Path, timeout: float = 60.0) -> tuple[Path, str]:
    """
    Baixa PDF de uma URL e retorna (caminho, hash).
    
    Args:
        url: URL do PDF
        dest_dir: Diretório de destino
        timeout: Timeout em segundos
        
    Returns:
        (Path do arquivo, SHA-256 hex)
    """
    headers = {"User-Agent": "UDA-Bot/1.0 (projeto-academico)"}
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.content
    except httpx.HTTPError as e:
        logger.error(f"Erro ao baixar {url}: {e}")
        raise
    
    file_hash = compute_bytes_hash(content)
    filename = f"{file_hash[:12]}.pdf"
    dest_path = dest_dir / filename
    
    dest_path.write_bytes(content)
    logger.info(f"PDF baixado: {dest_path} (hash={file_hash[:12]})")
    
    return dest_path, file_hash


class PDFDownloader:
    """Gerencia download, dedup e registro de PDFs."""
    
    def __init__(self, repo: CatalogRepository, storage_base: Path):
        """
        Args:
            repo: CatalogRepository para checagem de dedup
            storage_base: Caminho base para armazenamento (ex: data/pdfs)
        """
        self.repo = repo
        self.storage_base = Path(storage_base)
    
    async def ingest_pdf_url(
        self,
        url: str,
        empresa: str,
        ano: int | None = None,
        trimestre: int | None = None,
    ) -> tuple[str, str | None]:
        """
        Baixa PDF e registra se novo (dedup por hash).
        
        Args:
            url: URL do PDF
            empresa: Nome da construtora
            ano: Ano (inferido da URL se omitido)
            trimestre: Trimestre (inferido da URL se omitido)
            
        Returns:
            (status, document_id)
            - ('created', uuid) se novo
            - ('skipped', None) se duplicado
            - ('error', None) se falhou
        """
        try:
            # Inferir ano/trimestre da URL se não fornecido
            ano, trimestre = ano or 2025, trimestre or 1
            
            # Diretório de destino
            dest_dir = self.storage_base / empresa / str(ano) / f"T{trimestre}"
            
            # Download
            dest_path, file_hash = await download_pdf(url, dest_dir)
            
            # Verificar dedup
            if self.repo.document_exists_by_hash(file_hash):
                logger.info(f"PDF duplicado (hash={file_hash[:12]}), ignorando")
                dest_path.unlink(missing_ok=True)
                return "skipped", None
            
            # Criar documento no catálogo
            doc = self.repo.create_document(
                empresa=empresa,
                ano=ano,
                trimestre=trimestre,
                source_url=url,
                file_hash=file_hash,
                storage_path=str(dest_path),
            )
            
            logger.info(f"Documento criado: {doc.id} ({empresa} {ano}T{trimestre})")
            return "created", str(doc.id)
            
        except Exception as e:
            logger.exception(f"Erro ao ingerir {url}: {e}")
            return "error", None
