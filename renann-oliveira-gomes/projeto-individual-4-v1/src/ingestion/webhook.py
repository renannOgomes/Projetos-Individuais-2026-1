"""Ingestor via Webhooks com validação HMAC."""

import hashlib
import hmac
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class WebhookIngester:
    """Processa ingestão via webhooks com segurança HMAC."""
    
    def __init__(self, secret: str):
        """
        Args:
            secret: Chave compartilhada para validação HMAC-SHA256
        """
        self.secret = secret
    
    def verify_signature(
        self,
        payload_bytes: bytes,
        signature: str,
    ) -> bool:
        """
        Valida assinatura HMAC-SHA256 do webhook.
        
        Formato: "sha256=abc123..."
        
        Args:
            payload_bytes: Payload original em bytes
            signature: Header X-Webhook-Signature
            
        Returns:
            True se válido, False caso contrário
        """
        try:
            # Extrair algoritmo e hash
            if not signature.startswith("sha256="):
                logger.warning("Assinatura não começa com 'sha256='")
                return False
            
            provided_hash = signature[7:]  # Remove "sha256="
            
            # Computar hash esperado
            expected_hash = hmac.new(
                self.secret.encode(),
                payload_bytes,
                hashlib.sha256,
            ).hexdigest()
            
            # Comparar com timing-safe comparison
            return hmac.compare_digest(expected_hash, provided_hash)
            
        except Exception as e:
            logger.error(f"Erro ao validar assinatura: {e}")
            return False
    
    async def process_webhook(
        self,
        payload: dict[str, Any],
        signature: str,
        downloader,
    ) -> dict[str, Any]:
        """
        Processa notificação de webhook.
        
        Payload esperado:
        {
            "source": "MRV",
            "pdf_url": "https://ri.mrv.com.br/previa-3t25.pdf",
            "published_at": "2025-10-15T14:32:00Z",
            "signature": "sha256=abc123..."  # redundante, mas informativo
        }
        
        Args:
            payload: Dict com dados do webhook
            signature: Header X-Webhook-Signature
            downloader: PDFDownloader para fazer download
            
        Returns:
            Dict com status de processamento
            
        Raises:
            ValueError: Se assinatura inválida
        """
        # Validar assinatura
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        if not self.verify_signature(payload_bytes, signature):
            logger.error("Assinatura de webhook inválida")
            raise ValueError("Assinatura inválida")
        
        # Extrair informações
        source = payload.get("source")
        pdf_url = payload.get("pdf_url")
        
        if not source or not pdf_url:
            raise ValueError("Payload incompleto (source ou pdf_url faltando)")
        
        logger.info(f"Webhook válido: {source} - {pdf_url}")
        
        # Fazer download e ingerir
        status, doc_id = await downloader.ingest_pdf_url(
            url=pdf_url,
            empresa=source,
        )
        
        return {
            "status": "received",
            "source": source,
            "url": pdf_url,
            "ingestion_status": status,
            "document_id": doc_id,
        }


async def create_test_payload(
    source: str,
    pdf_url: str,
    secret: str,
) -> tuple[dict, str]:
    """
    Cria payload de teste com assinatura válida.
    
    Útil para testes e simulações.
    """
    payload = {
        "source": source,
        "pdf_url": pdf_url,
        "published_at": "2025-10-15T14:32:00Z",
    }
    
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    signature = "sha256=" + hmac.new(
        secret.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    
    return payload, signature
