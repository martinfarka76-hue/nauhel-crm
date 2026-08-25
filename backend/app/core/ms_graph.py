"""
Odesílání emailů přes Microsoft Graph API (aplikační OAuth - client
credentials flow, žádná interakce uživatele není potřeba).

Vyžaduje proměnné prostředí:
  MS_GRAPH_TENANT_ID, MS_GRAPH_CLIENT_ID, MS_GRAPH_CLIENT_SECRET,
  MS_GRAPH_SENDER_EMAIL (schránka, ze které se odesílá)

Pokud nejsou nastavené, odesílání se tiše přeskočí (zaloguje se info),
ať appka funguje i před dokončením Azure setupu - email je doplněk
k in-app notifikacím, ne nutná podmínka fungování CRM.
"""
import os
import time
import logging
import httpx

logger = logging.getLogger("nauhel_crm.ms_graph")

_token_cache = {"access_token": None, "expires_at": 0.0}


def _is_configured() -> bool:
    return all(
        [
            os.environ.get("MS_GRAPH_TENANT_ID"),
            os.environ.get("MS_GRAPH_CLIENT_ID"),
            os.environ.get("MS_GRAPH_CLIENT_SECRET"),
            os.environ.get("MS_GRAPH_SENDER_EMAIL"),
        ]
    )


def _get_access_token() -> str:
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["access_token"]

    tenant_id = os.environ["MS_GRAPH_TENANT_ID"]
    client_id = os.environ["MS_GRAPH_CLIENT_ID"]
    client_secret = os.environ["MS_GRAPH_CLIENT_SECRET"]

    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
    }
    resp = httpx.post(url, data=data, timeout=15.0)
    resp.raise_for_status()
    token_data = resp.json()
    _token_cache["access_token"] = token_data["access_token"]
    _token_cache["expires_at"] = now + token_data.get("expires_in", 3600)
    return _token_cache["access_token"]


def send_email(to_email: str, subject: str, body_html: str) -> bool:
    """
    Pošle email přes MS Graph. Vrací True při úspěchu, False při selhání
    nebo pokud integrace ještě není nakonfigurovaná. Nikdy nevyhazuje
    výjimku ven - volající kód (např. potvrzení objednávky) má fungovat
    normálně i když odeslání emailu selže.
    """
    if not _is_configured():
        logger.info("MS Graph není nakonfigurován - email se neodesílá (%s)", subject)
        return False

    try:
        token = _get_access_token()
        sender = os.environ["MS_GRAPH_SENDER_EMAIL"]
        url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": [{"emailAddress": {"address": to_email}}],
            },
            "saveToSentItems": True,
        }
        resp = httpx.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )
        resp.raise_for_status()
        logger.info("Email odeslán přes MS Graph: %s -> %s", subject, to_email)
        return True
    except Exception:
        logger.exception("Odeslání emailu přes MS Graph selhalo (%s)", subject)
        return False
