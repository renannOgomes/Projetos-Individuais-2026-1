from fastapi import FastAPI
from typing import List, Optional
from database import dados_conjuntura
from contract import ConjunturaHabitacional

app = FastAPI(title="API Conjuntura Habitacional - Ministério das Cidades")

@app.get("/api/conjuntura", response_model=List[ConjunturaHabitacional])
def get_conjuntura(
    empresa: Optional[str] = None, 
    ano: Optional[int] = None, 
    trimestre: Optional[int] = None
):
    resultados = dados_conjuntura
    if empresa:
        resultados = [r for r in resultados if r.empresa.lower() == empresa.lower()]
    if ano:
        resultados = [r for r in resultados if r.ano == ano]
    if trimestre:
        resultados = [r for r in resultados if r.trimestre == trimestre]
        
    return resultados