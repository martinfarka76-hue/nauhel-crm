"""
Tenká vrstva nad backendovými /api/mcp/* endpointy. Žádná byznys logika
tady - jen HTTP volání se sdíleným service tokenem (MCP_SERVICE_TOKEN),
stejná zásada jako u zbytku CRM (byznys logika výhradně v backendu).
"""
from typing import Any, Optional

import httpx

from app.settings import settings


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.backend_url,
        headers={"Authorization": f"Bearer {settings.service_token}"},
        timeout=15.0,
    )


async def list_deals(status: Optional[str] = None, company_name: Optional[str] = None) -> list[dict[str, Any]]:
    params = {k: v for k, v in {"status": status, "company_name": company_name}.items() if v}
    async with _client() as client:
        response = await client.get("/api/mcp/deals", params=params)
        response.raise_for_status()
        return response.json()


async def get_deal(deal_id: str) -> dict[str, Any]:
    async with _client() as client:
        response = await client.get(f"/api/mcp/deals/{deal_id}")
        response.raise_for_status()
        return response.json()


async def search_companies(query: str) -> list[dict[str, Any]]:
    async with _client() as client:
        response = await client.get("/api/mcp/companies", params={"q": query})
        response.raise_for_status()
        return response.json()


async def add_deal_note(
    deal_id: str, content: str, is_task: Optional[bool] = None, due_date: Optional[str] = None
) -> dict[str, Any]:
    payload = {"content": content, "is_task": is_task, "due_date": due_date}
    async with _client() as client:
        response = await client.post(f"/api/mcp/deals/{deal_id}/notes", json=payload)
        response.raise_for_status()
        return response.json()
