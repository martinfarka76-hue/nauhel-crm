"""
Sestavení MCPServer instance - OAuth (viz oauth_provider.py) + nástroje
(tools), které Claude uvidí po připojení konektoru.

Rozsah nástrojů odpovídá domluvené první verzi (9/2026): čtení pipeline
dealů a jejich detailu, vyhledání firmy, zápis poznámky/úkolu k dealu.
Žádné mazání, žádná změna stavu dealu, žádné citlivé operace - to
zůstává vyhrazené uživatelskému rozhraní CRM.
"""
from typing import Any, Optional

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.mcpserver.server import MCPServer

from app import crm_client
from app.oauth_provider import MCP_SCOPE, CrmOAuthProvider
from app.settings import settings


def build_server() -> MCPServer:
    public_url = settings.public_url.rstrip("/")
    oauth_provider = CrmOAuthProvider(auth_callback_url=f"{public_url}/login", server_url=public_url)

    auth_settings = AuthSettings(
        issuer_url=public_url,
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=[MCP_SCOPE],
            default_scopes=[MCP_SCOPE],
        ),
        required_scopes=[MCP_SCOPE],
        resource_server_url=None,  # legacy combined AS+RS mód, viz simple-auth SDK příklad
    )

    app = MCPServer(
        name="NAUHEL CRM",
        instructions=(
            "Nástroje pro čtení a jednoduché zápisy do NAUHEL CRM (obchodní "
            "případy/dealy, firmy, poznámky). Ceny, sazby a stavy dealů se "
            "NEMĚNÍ přes tyto nástroje - jen se čtou a doplňují poznámky."
        ),
        auth_server_provider=oauth_provider,
        auth=auth_settings,
    )

    @app.custom_route("/login", methods=["GET"])
    async def login_page_handler(request: Request) -> Response:
        state = request.query_params.get("state")
        if not state:
            raise HTTPException(400, "Chybí parametr state")
        return await oauth_provider.get_login_page(state)

    @app.custom_route("/login/callback", methods=["POST"])
    async def login_callback_handler(request: Request) -> Response:
        return await oauth_provider.handle_login_callback(request)

    @app.tool()
    async def list_deals(status: Optional[str] = None, company_name: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Vypíše obchodní případy (dealy) v pipeline NAUHEL CRM.

        Args:
            status: Volitelný filtr na přesný stav dealu (např. "Nabídka",
                "Objednávka", "Lead", "Kvalifikovaný lead", "Zálohová faktura",
                "Vyrobeno", "Fakturováno", "Ztraceno").
            company_name: Volitelný filtr - část názvu firmy (nerozlišuje
                velikost písmen).

        Returns:
            Seznam dealů (max. 200) - název, firma, stav, cena, vážený
            objem, očekávané datum uzavření, datum dalšího kontaktu.
        """
        return await crm_client.list_deals(status=status, company_name=company_name)

    @app.tool()
    async def get_deal(deal_id: str) -> dict[str, Any]:
        """
        Vrátí detail jednoho dealu podle ID: cenu, vážený objem, firmu,
        kontaktní osobu, existující dokumenty (nabídka/objednávka/...) a
        chronologické poznámky k případu.

        Args:
            deal_id: UUID dealu (získáš ho z výpisu list_deals).
        """
        return await crm_client.get_deal(deal_id)

    @app.tool()
    async def search_companies(query: str) -> list[dict[str, Any]]:
        """
        Vyhledá firmu v CRM podle (části) názvu nebo IČO.

        Args:
            query: Hledaný text (min. 2 znaky).
        """
        return await crm_client.search_companies(query)

    @app.tool()
    async def add_deal_note(
        deal_id: str,
        content: str,
        is_task: Optional[bool] = None,
        due_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Přidá poznámku k dealu - běžný zápis, nebo jednoduchý úkol.
        Poznámka se v CRM zobrazí s prefixem "[Claude]", ať je jasné, že
        nejde o ruční zápis obchodníka.

        Args:
            deal_id: UUID dealu, ke kterému se poznámka připojí.
            content: Text poznámky.
            is_task: True, pokud jde o úkol (má termín), jinak vynech.
            due_date: Termín úkolu ve formátu YYYY-MM-DD, jen pokud is_task=True.
        """
        return await crm_client.add_deal_note(deal_id, content, is_task=is_task, due_date=due_date)

    return app
