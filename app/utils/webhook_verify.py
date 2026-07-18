import hmac
import hashlib
import base64
import logging
from fastapi import Request

logger = logging.getLogger(__name__)


async def verify_webhook_signature(request: Request, secret: str) -> bool:
    """
    Verify the X-NombaVault-Signature header on an inbound Meroe webhook.

    Signing scheme (from OutboxWorkerService.java):
      signature = "t=" + epochSeconds + ",v1=" + base64(HMAC-SHA256(epochSeconds + "." + body, secret))
    """
    if not secret:
        logger.warning("MEROE_WEBHOOK_SECRET not configured — skipping signature verification")
        return True

    header = request.headers.get("X-NombaVault-Signature", "")
    if not header:
        logger.warning("Missing X-NombaVault-Signature header")
        return False

    # Parse t=...,v1=...
    parts = {}
    for item in header.split(","):
        if "=" in item:
            k, v = item.split("=", 1)
            parts[k.strip()] = v.strip()

    timestamp = parts.get("t")
    received_sig = parts.get("v1")
    if not timestamp or not received_sig:
        logger.warning(f"Malformed X-NombaVault-Signature: {header}")
        return False

    # Read raw body
    body = await request.body()
    body_str = body.decode("utf-8")

    # Compute expected signature
    sign_input = (timestamp + "." + body_str).encode("utf-8")
    key = secret.encode("utf-8")
    expected = base64.b64encode(
        hmac.new(key, sign_input, hashlib.sha256).digest()
    ).decode("utf-8")

    if not hmac.compare_digest(expected, received_sig):
        logger.warning("Webhook signature mismatch")
        return False

    return True
