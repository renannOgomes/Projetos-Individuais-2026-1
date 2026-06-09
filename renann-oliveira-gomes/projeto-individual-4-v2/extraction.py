import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from contract import ConjunturaHabitacional

load_dotenv()

def extract_metrics_with_gemini(text: str) -> ConjunturaHabitacional:
    """Processa o texto não estruturado utilizando o LLM e força o retorno no Contrato Semântico."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model_id = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    
    prompt = (
        "Você é um analista de engenharia de dados focado no setor habitacional do Brasil. "
        "Leia o texto extraído da prévia operacional (Relatório de RI) e extraia de forma rigorosa as métricas de negócio. "
        "Atenção: Ignore percentuais de variações destacadas no marketing e extraia SOMENTE os valores brutos operacionais "
        "do trimestre em questão.\n\n"
        f"TEXTO DO RELATÓRIO:\n{text[:60000]}" # Limite preventivo de contexto
    )
    
    max_retries = 4
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ConjunturaHabitacional,
                    temperature=0.0, # Zero para respostas estritamente literais e precisas
                ),
            )
            return ConjunturaHabitacional.model_validate_json(response.text)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 20  # Espera 20s, 40s e depois 60s
                    print(f"\n[Aviso] Limite de requisições da API atingido (429). Aguardando {wait_time}s antes de tentar novamente...")
                    time.sleep(wait_time)
                else:
                    print("\n[Erro] Cota gratuita diária excedida.")
                    raise e
            else:
                raise e