"""Parser de PDFs com estrutura hierárquica."""

from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass
class PageContent:
    """Conteúdo de uma página com metadados."""

    page_number: int
    text: str
    is_image: bool
    word_count: int


@dataclass
class DocumentStructure:
    """Estrutura hierárquica do documento."""

    title: str
    pages: list[PageContent]
    total_pages: int
    metadata: dict


def parse_pdf(pdf_path: Path) -> DocumentStructure:
    """Parse PDF com detecção de estrutura."""
    pages: list[PageContent] = []

    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            word_count = len(text.split())
            is_image = word_count < 50

            pages.append(
                PageContent(
                    page_number=i + 1,
                    text=text,
                    is_image=is_image,
                    word_count=word_count,
                )
            )

    return DocumentStructure(
        title=pdf_path.stem,
        pages=pages,
        total_pages=len(pages),
        metadata={"file_size": pdf_path.stat().st_size},
    )
