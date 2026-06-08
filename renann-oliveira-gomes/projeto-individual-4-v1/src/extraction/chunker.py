"""RAG Chunker com embeddings semânticos."""

import logging
from dataclasses import dataclass, field

import numpy as np

from src.extraction.embeddings import EmbeddingsManager
from src.extraction.parser import DocumentStructure

logger = logging.getLogger(__name__)

OPERATIONAL_KEYWORDS = {
    "vendas", "vgv", "vso", "estoque", "obras", "receita",
    "margem", "unidades", "operacional", "previa", "resultado",
}


@dataclass
class Chunk:
    """Trecho semântico do documento."""

    chunk_id: str
    page_number: int
    section: str
    text: str
    embedding: np.ndarray | None = field(default=None)
    is_image: bool = False
    word_count: int = 0


class RAGChunker:
    """Segmentação semântica com embeddings."""

    def __init__(self, embeddings_manager: EmbeddingsManager | None = None):
        """
        Inicializa com modelo de embeddings.
        
        Args:
            embeddings_manager: Manager para embeddings (opcional)
        """
        self.embeddings = embeddings_manager

    def chunk(self, doc_structure: DocumentStructure) -> list[Chunk]:
        """
        Chunking baseado em estrutura + embeddings.

        - Agrupa por seções (quebras duplas de linha)
        - Filtra seções muito curtas
        - Classifica como "operacional" ou "texto"
        - Computa embeddings para semantic search
        - Fallback se nenhum chunk for criado

        Args:
            doc_structure: Estrutura parseada do documento

        Returns:
            Lista de chunks prontos para extração
        """
        chunks: list[Chunk] = []

        for page in doc_structure.pages:
            if page.is_image:
                # Marcado para vision fallback
                chunks.append(
                    Chunk(
                        chunk_id=f"p{page.page_number}_img",
                        page_number=page.page_number,
                        section="image",
                        text="",
                        is_image=True,
                    )
                )
                continue

            # Split por linhas em branco (heurística de seções)
            sections = page.text.split("\n\n")
            for i, section_text in enumerate(sections):
                section_text = section_text.strip()
                
                # Filtrar seções muito curtas
                if len(section_text) < 10:
                    continue

                chunk_id = f"p{page.page_number}_s{i}"
                is_operational = self._is_operational(section_text)
                word_count = len(section_text.split())

                chunk = Chunk(
                    chunk_id=chunk_id,
                    page_number=page.page_number,
                    section="operacional" if is_operational else "texto",
                    text=section_text,
                    is_image=False,
                    word_count=word_count,
                )

                # Computar embeddings se model disponível
                if self.embeddings:
                    try:
                        chunk.embedding = self.embeddings.encode(section_text)
                    except Exception as e:
                        logger.warning(f"Erro ao computar embedding: {e}")
                        chunk.embedding = None

                chunks.append(chunk)

        # Fallback se nenhum chunk foi criado
        if not chunks:
            logger.warning("Nenhum chunk criado, usando fallback (primeira página)")
            return self._fallback_chunk(doc_structure)

        logger.info(f"Chunked: {len(chunks)} chunks")
        return chunks

    @staticmethod
    def _is_operational(text: str) -> bool:
        """
        Detecta se texto contém métricas operacionais.
        
        Args:
            text: Texto da seção
            
        Returns:
            True se contém keywords operacionais
        """
        lower = text.lower()
        return any(kw in lower for kw in OPERATIONAL_KEYWORDS)

    @staticmethod
    def _fallback_chunk(doc_structure: DocumentStructure) -> list[Chunk]:
        """
        Fallback se nenhum chunk for criado.
        
        Retorna primeira página como chunk único.
        """
        if doc_structure.pages:
            first_page = doc_structure.pages[0]
            return [
                Chunk(
                    chunk_id="p1_fallback",
                    page_number=1,
                    section="fallback",
                    text=first_page.text,
                    is_image=first_page.is_image,
                    word_count=first_page.word_count,
                )
            ]
        return []
