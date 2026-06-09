import os
import time
import requests
import schedule
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from main import processar_novo_relatorio

SOURCES = [
    {"empresa": "MRV", "ri_url": "https://ri.mrv.com.br", "resultados_path": "/central-de-resultados"},
    {"empresa": "Direcional", "ri_url": "https://ri.direcional.com.br", "resultados_path": "/resultados-trimestrais"},
    {"empresa": "Tenda", "ri_url": "https://ri.tenda.com", "resultados_path": "/central-de-resultados"},
    {"empresa": "Cury", "ri_url": "https://ricury.com.br", "resultados_path": "/central-de-resultados"},
    {"empresa": "Plano Plano", "ri_url": "https://ri.planoeplano.com.br", "resultados_path": "/central-de-resultados"}
]

def fetch_latest_pdf(empresa: str, ri_url: str, resultados_path: str) -> str:
    """Acessa a página de RI da empresa e tenta localizar o link do PDF mais recente de Prévia Operacional."""
    target_url = ri_url + resultados_path
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    print(f"\n[{empresa}] Verificando portal: {target_url}")
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[{empresa}] Erro ao acessar a página: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link['href'].lower()
        text = link.get_text(strip=True).lower()
        
        # Heurística: procura explicitamente por PDFs ou links que mencionem 'prévia'
        if '.pdf' in href or 'prévia' in text or 'previa' in text:
            pdf_url = urljoin(ri_url, link['href'])
            print(f"[{empresa}] Documento encontrado: {pdf_url}")
            return pdf_url
            
    print(f"[{empresa}] Nenhum documento compatível encontrado na página.")
    return None

def run_scraper_job():
    """Itera sobre as fontes, baixa os arquivos e envia para o Orquestrador UDA."""
    os.makedirs("downloads", exist_ok=True)
    
    for source in SOURCES:
        pdf_url = fetch_latest_pdf(source['empresa'], source['ri_url'], source['resultados_path'])
        
        if pdf_url:
            local_filename = f"downloads/{source['empresa']}_latest.pdf"
            print(f"[{source['empresa']}] Baixando arquivo...")
            
            try:
                pdf_response = requests.get(pdf_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                with open(local_filename, 'wb') as f:
                    f.write(pdf_response.content)
                    
                print(f"[{source['empresa']}] Acionando Worker do LLM...")
                processar_novo_relatorio(local_filename, pdf_url)
            except Exception as e:
                print(f"[{source['empresa']}] Falha ao processar o PDF: {e}")

if __name__ == "__main__":
    print("Iniciando o agendador... O scraper rodará imediatamente e depois toda segunda-feira às 08:00.")
    
    run_scraper_job() # Execução inicial
    
    schedule.every().monday.at("08:00").do(run_scraper_job)
    
    while True:
        schedule.run_pending()
        time.sleep(60) # Verifica a fila de agendamento a cada 60 segundos