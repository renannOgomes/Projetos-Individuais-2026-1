"""Scheduler com APScheduler para polling periódico."""

import asyncio
import logging
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.catalog.database import get_db_session, init_db
from src.catalog.repository import CatalogRepository
from src.config import get_settings
from src.ingestion.downloader import PDFDownloader
from src.ingestion.scraper import RIScraper

logger = logging.getLogger(__name__)


class ScheduledScanner:
    """Orquestrador de scan periódico das fontes RI."""
    
    def __init__(self):
        self.settings = get_settings()
        self.scraper = RIScraper()
        self.scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")
    
    async def run_scan(self) -> dict:
        """
        Executa um ciclo completo de varredura.
        
        Returns:
            Dict com estatísticas: {created, skipped, failed}
        """
        logger.info("=" * 60)
        logger.info("Iniciando scan das Centrais de Resultados...")
        logger.info("=" * 60)
        
        init_db()
        session = get_db_session()
        repo = CatalogRepository(session)
        downloader = PDFDownloader(repo, self.settings.pdf_storage_path)
        
        try:
            # Descobrir PDFs
            pdfs = await self.scraper.scan_all_sources()
            logger.info(f"Descobertos {len(pdfs)} PDFs potenciais")
            
            created = 0
            skipped = 0
            failed = 0
            
            # Ingerir cada PDF
            for pdf in pdfs:
                status, doc_id = await downloader.ingest_pdf_url(
                    url=pdf.url,
                    empresa=pdf.empresa,
                    ano=pdf.ano,
                    trimestre=pdf.trimestre,
                )
                
                if status == "created":
                    created += 1
                    logger.info(f"✓ Criado: {pdf.empresa} {pdf.ano}T{pdf.trimestre}")
                elif status == "skipped":
                    skipped += 1
                elif status == "error":
                    failed += 1
                    logger.error(f"✗ Erro: {pdf.empresa} - {pdf.url}")
            
            result = {
                "created": created,
                "skipped": skipped,
                "failed": failed,
                "total": len(pdfs),
            }
            
            logger.info("=" * 60)
            logger.info(f"Scan concluído:")
            logger.info(f"  - {created} novos")
            logger.info(f"  - {skipped} duplicados")
            logger.info(f"  - {failed} erros")
            logger.info("=" * 60)
            
            return result
            
        finally:
            session.close()
    
    def start(self, run_immediately: bool = True):
        """
        Inicia o scheduler com cron diário.
        
        Args:
            run_immediately: Se True, executa scan imediatamente
        """
        # Agendar cron
        self.scheduler.add_job(
            self.run_scan,
            CronTrigger(
                hour=self.settings.scan_cron_hour,
                minute=self.settings.scan_cron_minute,
                timezone="America/Sao_Paulo",
            ),
            id="ri_scan",
            name="Scan Centrais de Resultados",
        )
        
        logger.info(
            f"Scheduler iniciado. Próximo scan: "
            f"{self.settings.scan_cron_hour:02d}:"
            f"{self.settings.scan_cron_minute:02d} BRT"
        )
        
        if run_immediately:
            logger.info("Executando scan imediato...")
            asyncio.run(self.run_scan())
        
        self.scheduler.start()
    
    def stop(self):
        """Para o scheduler."""
        self.scheduler.shutdown()


def main():
    """Ponto de entrada para CLI: scheduler --once ou contínuo."""
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    scanner = ScheduledScanner()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        logger.info("Executando scan único...")
        asyncio.run(scanner.run_scan())
    else:
        logger.info("Iniciando scheduler em modo contínuo...")
        scanner.start(run_immediately=True)


if __name__ == "__main__":
    main()
