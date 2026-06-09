import hashlib
import pymupdf

def calculate_file_hash(file_path: str) -> str:
    """Calcula o hash SHA-256 do arquivo para evitar duplicidade de processamento no banco."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def extract_text_from_pdf(file_path: str, max_pages_full_scan: int = 15) -> str:
    """
    Extrai texto do PDF utilizando PyMuPDF.
    Aplica uma heurística de 'Semantic Chunking' baseada em palavras-chave para PDFs longos.
    """
    text = ""
    # Palavras-chave que indicam presença de resultados que queremos extrair
    keywords = ["vendas", "vgv", "vso", "estoque", "receita", "unidades", "operacional", "lançamento"]
    
    with pymupdf.open(file_path) as doc:
        num_pages = len(doc)
        for page_num in range(num_pages):
            page_text = doc[page_num].get_text()
            # Se for longo, só adiciona a página se contiver palavras-chave do negócio
            if num_pages <= max_pages_full_scan or any(kw in page_text.lower() for kw in keywords):
                text += f"\n--- PÁGINA {page_num + 1} ---\n{page_text}"
                
    return text