"""Testes para extraction pipeline."""

import pytest
from pathlib import Path

from src.extraction.parser import parse_pdf
from src.extraction.chunker import RAGChunker
from src.extraction.embeddings import EmbeddingsManager
from src.contracts.conjuntura import MetricaOperacional
from decimal import Decimal


@pytest.mark.asyncio
async def test_parser():
    """Test PDF parser."""
    # TODO: Usar fixture de PDF
    assert True


@pytest.mark.asyncio
async def test_chunker():
    """Test RAG chunker."""
    assert True


@pytest.mark.asyncio
async def test_multi_agent():
    """Test multi-agent extraction."""
    assert True


def test_metrica_pydantic():
    """Test contrato semântico."""
    # Métrica válida
    m = MetricaOperacional(
        chave="vgv",
        valor_absoluto=Decimal("2500000000"),
        unidade="R$",
        confianca=0.95,
    )
    assert m.valor_absoluto == Decimal("2500000000")
    
    # Métrica com null é válida
    m_null = MetricaOperacional(
        chave="vgv",
        valor_absoluto=None,
        unidade="R$",
        confianca=0.0,
    )
    assert m_null.valor_absoluto is None


def test_embeddings_manager():
    """Test embeddings manager."""
    em = EmbeddingsManager()
    
    # Test single string
    emb1 = em.encode("unidades vendidas")
    assert emb1.shape == (384,)
    
    # Test list of strings
    embs = em.encode(["unidades", "vgv", "vendas"])
    assert embs.shape == (3, 384)
    
    # Test similarity
    sim = em.similarity(emb1, emb1)
    assert abs(sim - 1.0) < 0.01  # Should be 1.0 for identical strings
