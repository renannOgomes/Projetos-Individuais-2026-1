"""Scraper de Centrais de Resultados com BeautifulSoup."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx
import yaml
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Keywords para filtrar PDFs de Prévia Operacional
PREVIA_KEYWORDS = re.compile(
    r"pr[eé]via\s+operacional|operational\s+preview|preview\s+operacional",
    re.IGNORECASE,
)


@dataclass
class PDFDiscovered:
    """PDF descoberto durante scan."""
    
    empresa: str
    url: str
    link_text: str
    ano: int | None = None
    trimestre: int | None = None


@dataclass
class SourceConfig:
    """Configuração de fonte RI."""
    
    empresa: str
    ri_url: str
    resultados_path: str = ""


def load_sources(config_path: Path | None = None) -> list[SourceConfig]:
    """Carrega fontes de sources.yaml."""
    if config_path is None:
        config_path = Path(__file__).resolve().parents[2] / "config" / "sources.yaml"
    
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    
    return [SourceConfig(**s) for s in data.get("sources", [])]


class RIScraper:
    """Scraper de Centrais de Resultados."""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "UDA-Bot/1.0 (projeto-academico-unb)"
        }
    
    async def discover_pdfs(self, source: SourceConfig) -> list[PDFDiscovered]:
        """
        Descobre PDFs em uma Central de Resultados.
        
        Args:
            source: Configuração da fonte RI
            
        Returns:
            Lista de PDFs descobertos
        """
        base_url = source.ri_url.rstrip("/")
        target_url = urljoin(
            base_url + "/",
            source.resultados_path.lstrip("/")
        ) if source.resultados_path else base_url
        
        try:
            async with httpx.AsyncClient(
                headers=self.headers,
                timeout=30.0,
                follow_redirects=True,
            ) as client:
                response = await client.get(target_url)
                response.raise_for_status()
                html = response.text
        except Exception as e:
            logger.warning(f"Erro ao acessar {target_url}: {e}")
            return []
        
        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")
        discovered: list[PDFDiscovered] = []
        
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)
            full_url = urljoin(target_url, href)
            
            # Filtrar apenas PDFs
            if not full_url.lower().endswith(".pdf"):
                continue
            
            # Filtrar por keywords
            combined = f"{text} {full_url}".lower()
            if not (
                PREVIA_KEYWORDS.search(combined)
                or "previa" in combined
                or "boletim" in combined
            ):
                continue
            
            # Inferir ano/trimestre do texto ou URL
            ano, trimestre = self._extract_period(text + " " + full_url)
            
            discovered.append(
                PDFDiscovered(
                    empresa=source.empresa,
                    url=full_url,
                    link_text=text,
                    ano=ano,
                    trimestre=trimestre,
                )
            )
        
        logger.info(f"Descobertos {len(discovered)} PDFs para {source.empresa}")
        return discovered
    
    @staticmethod
    def _extract_period(text: str) -> tuple[int | None, int | None]:
        """
        Extrai ano e trimestre do texto.
        
        Padrões:
        - "2025-3T" → (2025, 3)
        - "3T25" → (2025, 3)
        - "2025 Q2" → (2025, 2)
        """
        # Padrão: YYYY-NTou YYYY_N_T ou simples NTxx
        pattern = re.compile(
            r"(\d{4})\s*[_-]?\s*([1-4])\s*[Tt]|"  # 2025-3T ou 2025 3T
            r"([1-4])\s*[Tt]\s*(\d{2,4})",  # 3T25 ou 3T2025
            re.IGNORECASE
        )
        
        match = pattern.search(text)
        if match:
            if match.group(1):  # Formato YYYY-NT
                return int(match.group(1)), int(match.group(2))
            else:  # Formato NT_YYYY
                trimestre = int(match.group(3))
                year_str = match.group(4)
                ano = int(year_str) if len(year_str) == 4 else 2000 + int(year_str)
                return ano, trimestre
        
        # Fallback: buscar apenas ano
        year_match = re.search(r"20\d{2}", text)
        if year_match:
            return int(year_match.group(0)), 1
        
        return None, None
    
    async def scan_all_sources(
        self,
        config_path: Path | None = None
    ) -> list[PDFDiscovered]:
        """
        Varre todas as fontes RI.
        
        Args:
            config_path: Caminho de sources.yaml
            
        Returns:
            Lista agregada de PDFs descobertos
        """
        sources = load_sources(config_path)
        all_pdfs: list[PDFDiscovered] = []
        
        for source in sources:
            pdfs = await self.discover_pdfs(source)
            all_pdfs.extend(pdfs)
        
        return all_pdfs
