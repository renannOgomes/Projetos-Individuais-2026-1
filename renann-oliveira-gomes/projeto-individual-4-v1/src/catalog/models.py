"""Modelos de banco de dados com suporte a vector search."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Integer, DateTime, CHAR, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class Document(Base):
    """Documento ingerido (PDF)."""

    __tablename__ = "documents"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    empresa = Column(String, nullable=False)
    ano = Column(Integer, nullable=False)
    trimestre = Column(Integer, nullable=False)
    source_url = Column(String, unique=True)
    file_hash = Column(String, unique=True, nullable=False)
    storage_path = Column(String)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_document_hash", "file_hash"),
        Index("ix_document_empresa_trimestre", "empresa", "ano", "trimestre"),
    )


class MetricValue(Base):
    """Métrica extraída com linhagem completa."""

    __tablename__ = "metric_values"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    document_id = Column(String, nullable=False)
    chave = Column(String, nullable=False)
    valor_absoluto = Column(String)  # Decimal as string
    unidade = Column(String)
    pagina = Column(Integer)
    chunk_id = Column(String)
    trecho_evidencia = Column(String)
    tipo_extracao = Column(String, default="texto_livre")
    confianca = Column(Integer)  # 0-100
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_metric_document", "document_id"),
        Index("ix_metric_chave", "chave"),
    )


class SemanticChunk(Base):
    """Chunk com embedding para vector search."""

    __tablename__ = "semantic_chunks"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    document_id = Column(String, nullable=False)
    chunk_id = Column(String)
    page_number = Column(Integer)
    section = Column(String)
    text = Column(String, nullable=False)
    embedding = Column(Vector(384))  # Dimensão do all-MiniLM-L6-v2
    is_image = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_chunk_document", "document_id"),
        Index("ix_chunk_embedding", "embedding", postgresql_using="ivfflat"),
    )


class IngestEvent(Base):
    """Log de eventos de ingestão."""

    __tablename__ = "ingest_events"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    source_url = Column(String)
    event_type = Column(String)  # discovered, downloaded, duplicated, processed, failed
    status = Column(String)
    error_message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_event_type", "event_type"),
    )
