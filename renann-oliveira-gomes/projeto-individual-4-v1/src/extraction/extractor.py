"""Multi-agent extraction com LLM."""

import json
import logging
from decimal import Decimal
from pathlib import Path

import instructor
from google.genai import types

from src.contracts.conjuntura import Extracao, MetricaOperacional
from src.extraction.chunker import Chunk, RAGChunker
from src.extraction.embeddings import EmbeddingsManager
from src.extraction.parser import parse_pdf
from src.config import get_settings

logger = logging.getLogger(__name__)


class MultiAgentExtractor:
    """Extractor com múltiplos agentes especializados."""

    def __init__(
        self,
        embeddings_manager: EmbeddingsManager | None = None,
        llm_client=None,
    ):
        """
        Inicializa extractor.
        
        Args:
            embeddings_manager: Manager para embeddings
            llm_client: Cliente LLM (Gemini ou OpenAI)
        """
        self.embeddings = embeddings_manager
        self.chunker = RAGChunker(embeddings_manager)
        self.settings = get_settings()
        self.llm_client = llm_client or self._create_llm_client()

    def _create_llm_client(self):
        """Cria cliente LLM conforme provider configurado."""
        if self.settings.llm_provider == "gemini":
            import google.genai as genai
            
            genai.configure(api_key=self.settings.gemini_api_key)
            return instructor.patch(
                genai.GenerativeModel(self.settings.gemini_model),
                mode=instructor.Mode.TOOLS,
            )
        else:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.settings.openai_api_key)
            return instructor.patch(client)

    async def extract_from_pdf(
        self,
        pdf_path: Path,
        empresa: str,
        ano: int,
        trimestre: int,
    ) -> Extracao:
        """
        Pipeline completo de extração multi-agent.

        Fluxo:
        1. Parse e chunking semântico com RAG
        2. Para cada chunk:
           a. Agente 1: Classificação (tabela vs texto vs imagem)
           b. Agente 2: Extração Tabular (se tabela)
           c. Agente 3: Extração Textual (se texto)
        3. Agente 4: Merge e dedup
        4. Validação Pydantic

        Args:
            pdf_path: Caminho do PDF
            empresa: Nome da construtora
            ano: Ano de referência
            trimestre: Trimestre (1-4)

        Returns:
            Extracao validada
        """
        logger.info(f"Iniciando extração: {empresa} {ano}T{trimestre}")
        
        # Parse
        doc_structure = parse_pdf(pdf_path)
        logger.info(f"Parseado: {doc_structure.total_pages} páginas")
        
        # Chunking
        chunks = self.chunker.chunk(doc_structure)
        logger.info(f"Chunked: {len(chunks)} chunks")
        
        # Processamento de chunks
        all_metrics: dict[str, MetricaOperacional] = {}
        
        for chunk in chunks:
            if chunk.is_image:
                logger.debug(f"Pulando chunk imagem: {chunk.chunk_id}")
                continue  # TODO: Vision fallback
            
            # Agente 1: Classificação
            chunk_type = await self._classify_chunk(chunk)
            logger.debug(f"Chunk {chunk.chunk_id}: {chunk_type}")
            
            # Agente 2/3: Extração
            metrics = await self._extract_metrics(chunk, chunk_type)
            
            # Agente 4: Merge
            for metric in metrics:
                existing = all_metrics.get(metric.chave)
                if self._should_replace(metric, existing):
                    all_metrics[metric.chave] = metric
        
        logger.info(f"Extraídas {len(all_metrics)} métricas")
        
        result = Extracao(
            empresa=empresa,
            ano=ano,
            trimestre=trimestre,
            metricas=list(all_metrics.values()),
        )
        
        return result

    async def _classify_chunk(self, chunk: Chunk) -> str:
        """
        Agente 1: Classifica tipo de chunk.
        
        Returns: "tabela" | "texto_livre" | "imagem"
        """
        prompt = f"""
Você é um classificador de documentos financeiros.

Analise este trecho e determine se contém:
- Uma TABELA estruturada (linhas, colunas, alinhamento)
- TEXTO NARRATIVO (prosa contínua)
- Uma IMAGEM (sem texto extraível)

Responda com EXATAMENTE uma destas palavras, nada mais:
"tabela"
"texto_livre"
"imagem"

---
{chunk.text[:1000]}
"""
        
        try:
            response = await self.llm_client.messages.create(
                model=self.settings.gemini_model,
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}],
            )
            
            result = response.content[0].text.strip().lower()
            
            if "tabela" in result:
                return "tabela"
            elif "imagem" in result or "image" in result:
                return "imagem"
            else:
                return "texto_livre"
        
        except Exception as e:
            logger.error(f"Erro ao classificar chunk: {e}")
            return "texto_livre"  # Fallback

    async def _extract_metrics(
        self,
        chunk: Chunk,
        chunk_type: str,
    ) -> list[MetricaOperacional]:
        """
        Agente 2/3: Extrai métricas conforme tipo.
        
        Args:
            chunk: Chunk para processar
            chunk_type: "tabela" | "texto_livre" | "imagem"
            
        Returns:
            Lista de métricas extraídas
        """
        if chunk_type == "tabela":
            return await self._extract_from_table(chunk)
        elif chunk_type == "texto_livre":
            return await self._extract_from_text(chunk)
        else:
            logger.debug(f"Pulando chunk imagem: {chunk.chunk_id}")
            return []

    async def _extract_from_table(self, chunk: Chunk) -> list[MetricaOperacional]:
        """Agente 2: Extração de tabelas estruturadas."""
        prompt = f"""
Você é um especialista em extração de dados de TABELAS financeiras do setor imobiliário.

Esta é uma tabela de um relatório trimestral de construtora.

Extraia EXATAMENTE os valores numéricos das seguintes métricas (se presentes):
- unidades_vendidas: unidades
- vgv: R$ ou bilhões
- vso: percentual
- estoque_unidades: unidades
- obras_andamento: unidades
- receita_liquida: R$ ou bilhões
- margem_bruta: percentual

REGRAS:
1. Nunca invente valores
2. Se não encontrar, deixe vazio/null
3. Normalize números (2.5B = 2500000000)
4. Sempre cite a evidência textual

Tabela:
{chunk.text}

Responda em JSON:
{{
  "metricas": [
    {{
      "chave": "vgv",
      "valor_absoluto": "2500000000",
      "unidade": "R$",
      "confianca": 0.95,
      "trecho_evidencia": "...",
      "tipo_extracao": "tabela"
    }}
  ]
}}
"""
        
        try:
            response = await self._call_llm_structured(prompt)
            metrics = self._parse_metrics_response(response, "tabela", chunk)
            return metrics
        except Exception as e:
            logger.error(f"Erro ao extrair de tabela: {e}")
            return []

    async def _extract_from_text(self, chunk: Chunk) -> list[MetricaOperacional]:
        """Agente 3: Extração de texto narrativo."""
        prompt = f"""
Você é um analista de dados do setor imobiliário.

Este texto contém informações operacionais de um trimestre.

Extraia as métricas absolutas mencionadas:
- Unidades vendidas
- VGV (Valor Geral de Vendas)
- VSO (Velocidade sobre Oferta) em %
- Estoque de unidades
- Obras em andamento
- Receita líquida
- Margem bruta %

REGRAS RIGOROSAS:
1. Valores ABSOLUTOS. Ignore "+15% vs 3T24"
2. Se não encontrar, null
3. Se ambiguidade, null (NÃO invente)
4. Sempre cite trecho que prova
5. Confiança textual: 0.70

Texto:
{chunk.text}

Responda em JSON:
{{
  "metricas": [
    {{
      "chave": "unidades_vendidas",
      "valor_absoluto": "4230",
      "unidade": "unidades",
      "confianca": 0.70,
      "trecho_evidencia": "...",
      "tipo_extracao": "texto_livre"
    }}
  ]
}}
"""
        
        try:
            response = await self._call_llm_structured(prompt)
            metrics = self._parse_metrics_response(response, "texto_livre", chunk)
            return metrics
        except Exception as e:
            logger.error(f"Erro ao extrair de texto: {e}")
            return []

    async def _call_llm_structured(self, prompt: str) -> dict:
        """Chama LLM com parsing de JSON estruturado."""
        try:
            response = await self.llm_client.messages.create(
                model=self.settings.gemini_model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            
            text = response.content[0].text
            
            # Tentar extrair JSON do response
            try:
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                json_str = text[json_start:json_end]
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                logger.error(f"Não conseguiu fazer parse de JSON: {text[:100]}")
                return {"metricas": []}
        
        except Exception as e:
            logger.error(f"Erro ao chamar LLM: {e}")
            return {"metricas": []}

    def _parse_metrics_response(
        self,
        response: dict,
        tipo_extracao: str,
        chunk: Chunk,
    ) -> list[MetricaOperacional]:
        """Parseia resposta do LLM em MetricasOperacionais."""
        metrics = []
        
        for metric_data in response.get("metricas", []):
            try:
                # Converter valor absoluto
                valor_abs = None
                if metric_data.get("valor_absoluto"):
                    try:
                        valor_abs = Decimal(str(metric_data["valor_absoluto"]))
                    except:
                        pass
                
                metric = MetricaOperacional(
                    chave=metric_data.get("chave"),
                    valor_absoluto=valor_abs,
                    unidade=metric_data.get("unidade", ""),
                    pagina=chunk.page_number,
                    secao=chunk.section,
                    tipo_extracao=tipo_extracao,
                    confianca=float(metric_data.get("confianca", 0.7)),
                    trecho_evidencia=metric_data.get("trecho_evidencia"),
                    chunk_id=chunk.chunk_id,
                )
                metrics.append(metric)
            except Exception as e:
                logger.warning(f"Erro ao parsear métrica: {e}")
        
        return metrics

    @staticmethod
    def _should_replace(
        metric: MetricaOperacional,
        existing: MetricaOperacional | None,
    ) -> bool:
        """
        Decide se deve substituir métrica existente.
        
        Preferências:
        1. Maior confiança
        2. Se igual, com evidência textual
        3. Se igual, tipo=tabela (mais preciso)
        """
        if existing is None:
            return True
        
        if metric.confianca > existing.confianca:
            return True
        
        if metric.confianca == existing.confianca:
            if metric.trecho_evidencia and not existing.trecho_evidencia:
                return True
            if metric.tipo_extracao == "tabela" and existing.tipo_extracao != "tabela":
                return True
        
        return False
