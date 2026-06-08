"""Gerenciamento de embeddings com sentence-transformers."""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingsManager:
    """Gerencia embeddings com sentence-transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        """
        Inicializa modelo de embeddings.
        
        Args:
            model_name: Nome do modelo SentenceTransformer
            device: "cpu" ou "cuda"
        """
        try:
            from sentence_transformers import SentenceTransformer
            
            self.model = SentenceTransformer(model_name, device=device)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(
                f"Modelo de embeddings carregado: {model_name} ({self.dimension}d)"
            )
        except ImportError:
            logger.error(
                "sentence-transformers não instalado. "
                "Instale com: pip install sentence-transformers"
            )
            self.model = None
            self.dimension = 384
    
    def encode(self, texts: str | list[str]) -> np.ndarray:
        """
        Codifica texto(s) como embedding(s).
        
        Args:
            texts: String ou lista de strings
            
        Returns:
            Array numpy (N, 384) onde N é número de textos
        """
        if self.model is None:
            logger.warning(
                "Modelo de embeddings não disponível. "
                "Retornando embedding nulo."
            )
            if isinstance(texts, str):
                return np.zeros(self.dimension)
            return np.zeros((len(texts), self.dimension))
        
        if isinstance(texts, str):
            return self.model.encode(texts, show_progress_bar=False)
        
        return self.model.encode(texts, show_progress_bar=False)
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calcula similaridade cosseno entre dois embeddings.
        
        Args:
            embedding1: Array (384,)
            embedding2: Array (384,)
            
        Returns:
            Similarity score [0, 1]
        """
        from sklearn.metrics.pairwise import cosine_similarity
        
        sim = cosine_similarity([embedding1], [embedding2])[0][0]
        return float(sim)


def create_embeddings_manager() -> Optional[EmbeddingsManager]:
    """Factory para criar embeddings manager."""
    try:
        return EmbeddingsManager()
    except Exception as e:
        logger.error(f"Erro ao criar embeddings manager: {e}")
        return None
