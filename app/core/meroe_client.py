"""
Thin async client for the Meroe (NombaVault) BaaS API.
Zola's backend uses this to provision customers, check balances,
list transactions, and request payouts.
"""
import httpx
from fastapi import HTTPException
from app.core.config import get_settings

settings = get_settings()

_client: httpx.AsyncClient | None = None


def get_meroe_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.meroe_base_url,
            headers={
                "X-API-Key": settings.meroe_api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    return _client


async def meroe_post(path: str, body: dict) -> dict:
    client = get_meroe_client()
    resp = await client.post(path, json=body)
    _raise_for_meroe(resp)
    return resp.json()


async def meroe_get(path: str, params: dict = None) -> dict:
    client = get_meroe_client()
    resp = await client.get(path, params=params)
    _raise_for_meroe(resp)
    return resp.json()


def _raise_for_meroe(resp: httpx.Response):
    if resp.status_code < 400:
        return
    try:
        detail = resp.json().get("message") or resp.json().get("detail") or resp.text
    except Exception:
        detail = resp.text
    raise HTTPException(status_code=resp.status_code, detail=f"Meroe error: {detail}")
