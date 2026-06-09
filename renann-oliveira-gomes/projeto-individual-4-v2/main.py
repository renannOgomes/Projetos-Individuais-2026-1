import os
import argparse
import glob
from ingestion import calculate_file_hash, extract_text_from_pdf
from extraction import extract_metrics_with_gemini
from database import processed_hashes, dados_conjuntura

def processar_novo_relatorio(caminho_pdf: str, source_url: str):
    """Pipeline principal executado toda vez que um novo PDF é detectado."""
    print(f"[{caminho_pdf}] Iniciando pipeline...")
    
    # 1. Idempotência e Linhagem
    file_hash = calculate_file_hash(caminho_pdf)
    if file_hash in processed_hashes:
        print(f"[{caminho_pdf}] Arquivo ignorado - já computado no catálogo (Hash: {file_hash}).")
        return
        
    # 2. Ingestão - Extração Bruta
    print(f"[{caminho_pdf}] Extraindo layout do arquivo via PyMuPDF...")
    texto_bruto = extract_text_from_pdf(caminho_pdf)
    
    # 3. Módulo UDA - Inteligência Artificial
    print(f"[{caminho_pdf}] Interrogando LLM Gemini via Contrato Semântico...")
    dados_estruturados = extract_metrics_with_gemini(texto_bruto)
    
    # 4. Inserção no Catálogo
    processed_hashes.add(file_hash)
    dados_conjuntura.append(dados_estruturados)
    print(f"[{caminho_pdf}] Processamento Finalizado! Registros armazenados no banco.")
    print(f"Output: {dados_estruturados.model_dump_json(indent=2)}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline UDA - Ingestão de PDFs")
    parser.add_argument("--folder", type=str, help="Caminho da pasta contendo os PDFs para processamento em lote")
    parser.add_argument("--file", type=str, help="Caminho de um arquivo PDF específico para processamento")
    
    args = parser.parse_args()

    if args.folder:
        folder_path = args.folder
        print(f"Buscando PDFs na pasta: {folder_path}")
        pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
        if not pdf_files:
            print("Nenhum arquivo PDF encontrado na pasta informada.")
        for pdf_path in pdf_files:
            processar_novo_relatorio(pdf_path, source_url="upload_local_lote")
    elif args.file:
        processar_novo_relatorio(args.file, source_url="upload_local")
    else:
        print("Orquestrador pronto.")
        print("Dica: Use 'python main.py --folder <caminho>' ou 'python main.py --file <caminho>' para ingestão manual.")