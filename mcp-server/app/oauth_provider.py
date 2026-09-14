"""
OAuth authorization server provider pro NAUHEL CRM MCP konektor.

Vychází z oficiálního ukázkového provideru v Python MCP SDK
(examples/servers/simple-auth/mcp_simple_auth/simple_auth_provider.py),
upraveného pro reálné jednouživatelské nasazení:

- přihlašování jen heslem (žádné uživatelské jméno - jediný uživatel),
- registrovaní klienti a vydané tokeny se ukládají na disk (JSON soubor),
  ať se po restartu kontejneru nemusí Claude znovu autorizovat,
- podpora refresh tokenů (v ukázkovém provideru chybí), ať přihlášení
  vydrží dlouhodobě bez opakovaného ručního loginu.

Toto NENÍ obecný víceuživatelský OAuth server - je to záměrně
zjednodušené na jednoho uživatele (Martina), stejně jako zbytek MCP
integrace (viz /areas/... poznámky k rozhodnutí).
"""

import json
import secrets
import time
from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from app.settings import settings

MCP_SCOPE = "crm"
ACCESS_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 dní
REFRESH_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 180  # 180 dní


class CrmOAuthProvider(OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]):
    def __init__(self, auth_callback_url: str, server_url: str):
        self.auth_callback_url = auth_callback_url
        self.server_url = server_url

        self._state_path = Path(settings.data_dir) / "oauth_state.json"
        self.clients: dict[str, OAuthClientInformationFull] = {}
        self.auth_codes: dict[str, AuthorizationCode] = {}
        self.tokens: dict[str, AccessToken] = {}
        self.refresh_tokens: dict[str, RefreshToken] = {}
        self.state_mapping: dict[str, dict[str, str | None]] = {}
        self._load()

    # --- Perzistence (klienti + tokeny přežijí restart kontejneru) -----

    def _load(self) -> None:
        if not self._state_path.exists():
            return
        try:
            data = json.loads(self._state_path.read_text())
        except (json.JSONDecodeError, OSError):
            return
        self.clients = {
            cid: OAuthClientInformationFull.model_validate(c) for cid, c in data.get("clients", {}).items()
        }
        self.tokens = {t: AccessToken.model_validate(v) for t, v in data.get("tokens", {}).items()}
        self.refresh_tokens = {
            t: RefreshToken.model_validate(v) for t, v in data.get("refresh_tokens", {}).items()
        }

    def _save(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "clients": {cid: c.model_dump(mode="json") for cid, c in self.clients.items()},
            "tokens": {t: v.model_dump(mode="json") for t, v in self.tokens.items()},
            "refresh_tokens": {t: v.model_dump(mode="json") for t, v in self.refresh_tokens.items()},
        }
        self._state_path.write_text(json.dumps(data))

    # --- Registrace klienta (DCR) ---------------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        if not client_info.client_id:
            raise ValueError("No client_id provided")
        self.clients[client_info.client_id] = client_info
        self._save()

    # --- Autorizace (přihlašovací stránka) ------------------------------

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        state = params.state or secrets.token_hex(16)
        self.state_mapping[state] = {
            "redirect_uri": str(params.redirect_uri),
            "code_challenge": params.code_challenge,
            "redirect_uri_provided_explicitly": str(params.redirect_uri_provided_explicitly),
            "client_id": client.client_id,
            "resource": params.resource,
        }
        return f"{self.auth_callback_url}?state={state}"

    async def get_login_page(self, state: str) -> HTMLResponse:
        if not state:
            raise HTTPException(400, "Chybí parametr state")

        html_content = f"""
        <!DOCTYPE html>
        <html lang="cs">
        <head>
            <meta charset="utf-8">
            <title>NAUHEL CRM - přihlášení Claude</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 420px; margin: 80px auto; padding: 20px; }}
                h2 {{ margin-bottom: 4px; }}
                p.hint {{ color: #666; font-size: 14px; }}
                input {{ width: 100%; padding: 10px; margin-top: 6px; box-sizing: border-box; }}
                button {{ background-color: #b5652d; color: white; padding: 10px 15px; border: none;
                          cursor: pointer; margin-top: 16px; width: 100%; font-size: 15px; }}
            </style>
        </head>
        <body>
            <h2>NAUHEL CRM</h2>
            <p class="hint">Přihlášení pro připojení Claude ke CRM datům.</p>
            <form action="{self.server_url.rstrip("/")}/login/callback" method="post">
                <input type="hidden" name="state" value="{state}">
                <label>Heslo</label>
                <input type="password" name="password" required autofocus>
                <button type="submit">Přihlásit</button>
            </form>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    async def handle_login_callback(self, request: Request) -> Response:
        form = await request.form()
        password = form.get("password")
        state = form.get("state")

        if not password or not state or not isinstance(password, str) or not isinstance(state, str):
            raise HTTPException(400, "Chybí heslo nebo state parametr")

        redirect_uri = await self._complete_login(password, state)
        return RedirectResponse(url=redirect_uri, status_code=302)

    async def _complete_login(self, password: str, state: str) -> str:
        state_data = self.state_mapping.get(state)
        if not state_data:
            raise HTTPException(400, "Neplatný nebo expirovaný state parametr")

        redirect_uri = state_data["redirect_uri"]
        code_challenge = state_data["code_challenge"]
        redirect_uri_provided_explicitly = state_data["redirect_uri_provided_explicitly"] == "True"
        client_id = state_data["client_id"]
        resource = state_data.get("resource")
        assert redirect_uri is not None
        assert code_challenge is not None
        assert client_id is not None

        if not settings.login_password or password != settings.login_password:
            raise HTTPException(401, "Nesprávné heslo")

        new_code = f"mcp_{secrets.token_hex(16)}"
        self.auth_codes[new_code] = AuthorizationCode(
            code=new_code,
            client_id=client_id,
            redirect_uri=AnyHttpUrl(redirect_uri),
            redirect_uri_provided_explicitly=redirect_uri_provided_explicitly,
            expires_at=time.time() + 300,
            scopes=[MCP_SCOPE],
            code_challenge=code_challenge,
            resource=resource,
            subject="martin",
        )
        del self.state_mapping[state]
        return construct_redirect_uri(redirect_uri, code=new_code, state=state)

    # --- Výměna autorizačního kódu za tokeny ----------------------------

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        return self.auth_codes.get(authorization_code)

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        if authorization_code.code not in self.auth_codes:
            raise ValueError("Neplatný authorization code")
        if not client.client_id:
            raise ValueError("No client_id provided")

        access_token, refresh_token = self._issue_tokens(client.client_id, authorization_code.scopes, authorization_code.resource)
        del self.auth_codes[authorization_code.code]
        self._save()

        return OAuthToken(
            access_token=access_token.token,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_TTL_SECONDS,
            scope=" ".join(access_token.scopes),
            refresh_token=refresh_token.token,
        )

    # --- Access token ----------------------------------------------------

    async def load_access_token(self, token: str) -> AccessToken | None:
        access_token = self.tokens.get(token)
        if not access_token:
            return None
        if access_token.expires_at and access_token.expires_at < time.time():
            del self.tokens[token]
            self._save()
            return None
        return access_token

    # --- Refresh token (chybí v oficiálním demo provideru - doplněno) ---

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        token = self.refresh_tokens.get(refresh_token)
        if not token or token.client_id != client.client_id:
            return None
        if token.expires_at and token.expires_at < time.time():
            del self.refresh_tokens[refresh_token]
            self._save()
            return None
        return token

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        # Rotace: starý refresh token zneplatníme, vydáme nový (společně s novým access tokenem).
        if refresh_token.token in self.refresh_tokens:
            del self.refresh_tokens[refresh_token.token]

        access_token, new_refresh_token = self._issue_tokens(
            client.client_id, refresh_token.scopes, refresh_token.resource
        )
        self._save()

        return OAuthToken(
            access_token=access_token.token,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_TTL_SECONDS,
            scope=" ".join(access_token.scopes),
            refresh_token=new_refresh_token.token,
        )

    def _issue_tokens(self, client_id: str, scopes: list[str], resource: str | None) -> tuple[AccessToken, RefreshToken]:
        access_token = AccessToken(
            token=f"mcp_{secrets.token_hex(32)}",
            client_id=client_id,
            scopes=scopes,
            expires_at=int(time.time()) + ACCESS_TOKEN_TTL_SECONDS,
            resource=resource,
            subject="martin",
        )
        refresh_token = RefreshToken(
            token=f"mcp_refresh_{secrets.token_hex(32)}",
            client_id=client_id,
            scopes=scopes,
            expires_at=int(time.time()) + REFRESH_TOKEN_TTL_SECONDS,
            resource=resource,
            subject="martin",
        )
        self.tokens[access_token.token] = access_token
        self.refresh_tokens[refresh_token.token] = refresh_token
        return access_token, refresh_token

    async def revoke_token(self, token: str, token_type_hint: str | None = None) -> None:  # type: ignore[override]
        changed = False
        if token in self.tokens:
            del self.tokens[token]
            changed = True
        if token in self.refresh_tokens:
            del self.refresh_tokens[token]
            changed = True
        if changed:
            self._save()
