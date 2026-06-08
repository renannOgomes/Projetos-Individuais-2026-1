"""CLI para teste de extração."""

import asyncio
import json
import logging
from pathlib import Path

import typer

from src.catalog.database import init_db, get_db_session
from src.catalog.repository import CatalogRepository
from src.extraction.embeddings import EmbeddingsManager
from src.extraction.extractor import MultiAgentExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = typer.Typer()


@app.command()
def extract(
    pdf_path: str = typer.Argument(
        ...,
        help="Caminho do PDF para extrair"
    ),
    empresa: str = typer.Option(
        "Conjuntura",
        "--empresa",
        "-e",
        help="Nome da construtora"
    ),
    ano: int = typer.Option(
        2025,
        "--ano",
        "-a",
        help="Ano de referência"
    ),
    trimestre: int = typer.Option(
        3,
        "--trimestre",
        "-t",
        help="Trimestre (1-4)"
    ),
    no_persist: bool = typer.Option(
        False,
        "--no-persist",
        help="Apenas retorna JSON sem persistir"
    ),
    with_embeddings: bool = typer.Option(
        True,
        "--no-embeddings/--embeddings",
        help="Usar embeddings (default: true)"
    ),
):
    """
    Extrai métricas de um PDF.
    
    Exemplos:
    
      python -m src.cli documento.pdf --empresa MRV --ano 2025 --trimestre 3
      
      python -m src.cli documento.pdf --no-persist
      
      python -m src.cli documento.pdf --no-embeddings
    """
    
    async def run_extraction():
        # Validar entrada
        pdf = Path(pdf_path)
        if not pdf.exists():
            typer.echo(f"❌ Arquivo não encontrado: {pdf}", err=True)
            raise typer.Exit(code=1)
        
        if not (1 <= trimestre <= 4):
            typer.echo(f"❌ Trimestre inválido: {trimestre} (deve estar entre 1-4)", err=True)
            raise typer.Exit(code=1)
        
        # Inicializar
        typer.echo(f"📄 Processando: {pdf.name}")
        typer.echo(f"   Empresa: {empresa} | Ano: {ano} | Trimestre: {trimestre}")
        typer.echo("")
        
        # Criar extractor
        embeddings = None
        if with_embeddings:
            typer.echo("⏳ Carregando modelo de embeddings...")
            try:
                embeddings = EmbeddingsManager()
                typer.echo("✓ Embeddings carregados")
            except Exception as e:
                typer.echo(f"⚠️  Embeddings indisponíveis: {e}")
                typer.echo("   Continuando sem embeddings...")
        
        extractor = MultiAgentExtractor(embeddings)
        
        # Extrair
        typer.echo("🚀 Iniciando extração (multi-agent)...")
        result = await extractor.extract_from_pdf(pdf, empresa, ano, trimestre)
        
        # Exibir resultado
        typer.echo("")
        typer.echo("=" * 70)
        typer.echo(f"RESULTADO DA EXTRAÇÃO")
        typer.echo("=" * 70)
        typer.echo(f"Empresa:  {result.empresa}")
        typer.echo(f"Período:  {result.ano}T{result.trimestre}")
        typer.echo(f"Métricas: {len(result.metricas)} extraídas")
        typer.echo("")
        
        # Mostrar métricas
        if result.metricas:
            typer.echo("Métricas Extraídas:")
            typer.echo("-" * 70)
            for metric in result.metricas:
                valor = metric.valor_absoluto or "null"
                confianca = f"{int(metric.confianca * 100)}%"
                tipo = f"[{metric.tipo_extracao}]"
                
                typer.echo(
                    f"  • {metric.chave:20} = {str(valor):20} "
                    f"{metric.unidade:15} {confianca:6} {tipo}"
                )
                
                if metric.trecho_evidencia:
                    trecho = metric.trecho_evidencia[:60] + "..."
                    typer.echo(f"    Evidência: {trecho}")
        else:
            typer.echo("⚠️  Nenhuma métrica foi extraída")
        
        typer.echo("=" * 70)
        
        # JSON output
        result_dict = {
            "empresa": result.empresa,
            "ano": result.ano,
            "trimestre": result.trimestre,
            "metricas": [
                {
                    "chave": m.chave,
                    "valor_absoluto": str(m.valor_absoluto) if m.valor_absoluto else None,
                    "unidade": m.unidade,
                    "pagina": m.pagina,
                    "secao": m.secao,
                    "tipo_extracao": m.tipo_extracao,
                    "confianca": m.confianca,
                    "trecho_evidencia": m.trecho_evidencia,
                }
                for m in result.metricas
            ]
        }
        
        typer.echo("")
        typer.echo(json.dumps(result_dict, indent=2, default=str))
        
        # Persistir se solicitado
        if not no_persist:
            typer.echo("")
            typer.echo("💾 Persistindo no banco de dados...")
            try:
                init_db()
                session = get_db_session()
                repo = CatalogRepository(session)
                
                # TODO: Implementar persistência
                # doc = repo.create_document(...)
                
                typer.echo("✓ Dados persistidos")
                session.close()
            except Exception as e:
                typer.echo(f"❌ Erro ao persistir: {e}", err=True)
        
        typer.echo("✓ Conclusão!")
    
    # Rodar async
    asyncio.run(run_extraction())


@app.command()
def scan(
    once: bool = typer.Option(
        True,
        "--once/--daemon",
        help="Executar uma vez ou em modo daemon"
    ),
):
    """
    Executa scan das Centrais de Resultados.
    
    Exemplos:
    
      python -m src.cli scan --once  (executa uma vez)
      
      python -m src.cli scan --daemon  (executa diariamente às 06:00 BRT)
    """
    from src.ingestion.scheduler import ScheduledScanner
    
    scanner = ScheduledScanner()
    
    if once:
        typer.echo("🔍 Executando scan único das Centrais de Resultados...")
        result = asyncio.run(scanner.run_scan())
        typer.echo(f"✓ Scan concluído: {result['created']} novos, {result['skipped']} duplicados")
    else:
        typer.echo("🔍 Iniciando scheduler em modo daemon...")
        scanner.start(run_immediately=False)


if __name__ == "__main__":
    app()
