"""Repositório de catálogo com vector search."""

from sqlalchemy.orm import Session

from src.catalog.models import Document, MetricValue, SemanticChunk, IngestEvent


class CatalogRepository:
    """Acesso aos dados com operações de vector search."""

    def __init__(self, session: Session):
        self.session = session

    def document_exists_by_hash(self, file_hash: str) -> bool:
        """Verifica se documento com este hash já existe."""
        return self.session.query(Document).filter_by(file_hash=file_hash).first() is not None

    def create_document(
        self,
        empresa: str,
        ano: int,
        trimestre: int,
        source_url: str,
        file_hash: str,
        storage_path: str,
    ) -> Document:
        """Cria novo documento no catálogo."""
        doc = Document(
            empresa=empresa,
            ano=ano,
            trimestre=trimestre,
            source_url=source_url,
            file_hash=file_hash,
            storage_path=storage_path,
        )
        self.session.add(doc)
        self.session.commit()
        return doc

    def save_semantic_chunk(
        self,
        document_id: str,
        chunk_id: str,
        page_number: int,
        section: str,
        text: str,
        embedding: list[float],
    ) -> SemanticChunk:
        """Salva chunk com embedding para vector search."""
        chunk = SemanticChunk(
            document_id=document_id,
            chunk_id=chunk_id,
            page_number=page_number,
            section=section,
            text=text,
            embedding=embedding,
        )
        self.session.add(chunk)
        self.session.commit()
        return chunk

    def save_metric(
        self,
        document_id: str,
        chave: str,
        valor_absoluto: str | None,
        unidade: str,
        pagina: int | None,
        chunk_id: str | None,
        trecho_evidencia: str | None,
        tipo_extracao: str,
        confianca: int,
    ) -> MetricValue:
        """Salva métrica extraída com linhagem."""
        metric = MetricValue(
            document_id=document_id,
            chave=chave,
            valor_absoluto=valor_absoluto,
            unidade=unidade,
            pagina=pagina,
            chunk_id=chunk_id,
            trecho_evidencia=trecho_evidencia,
            tipo_extracao=tipo_extracao,
            confianca=confianca,
        )
        self.session.add(metric)
        self.session.commit()
        return metric
