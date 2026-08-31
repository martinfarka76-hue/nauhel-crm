"""
Integrace se SharePointem (automatické vytváření složek zakázek podle
šablony, nahrávání souborů) přes Microsoft Graph. Používá stejnou
aplikaci (client_id/secret) jako MS Graph email integrace - jen s
navíc přiděleným oprávněním Sites.ReadWrite.All.

Vyžaduje proměnné prostředí:
  MS_GRAPH_TENANT_ID, MS_GRAPH_CLIENT_ID, MS_GRAPH_CLIENT_SECRET (sdílené s ms_graph.py)
  SHAREPOINT_SITE_HOSTNAME (např. "nauhel.sharepoint.com")
  SHAREPOINT_SITE_PATH (např. "/sites/NAUHELs.r.o81")
  SHAREPOINT_LIBRARY_NAME (výchozí "Sdílené dokumenty")
  SHAREPOINT_ZAKAZKY_FOLDER (výchozí "03_Zakázky")

Pokud nejsou nastavené, veškerá volání se tiše přeskočí - stejný vzor
jako u ms_graph.py a idoklad.py.
"""
import os
import time
import logging
import httpx

logger = logging.getLogger("nauhel_crm.sharepoint")

_token_cache = {"access_token": None, "expires_at": 0.0}
_site_cache = {"site_id": None, "drive_id": None, "zakazky_folder_id": None}

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

SUBFOLDERS = [
    "01_Poptávka",
    "02_Nabídka",
    "03_Realizace",
    "04_Fakturace",
    "05_Foto z realizace",
    "06_Smlouvy a specifikace",
]


def is_configured() -> bool:
    return all(
        [
            os.environ.get("MS_GRAPH_TENANT_ID"),
            os.environ.get("MS_GRAPH_CLIENT_ID"),
            os.environ.get("MS_GRAPH_CLIENT_SECRET"),
            os.environ.get("SHAREPOINT_SITE_HOSTNAME"),
            os.environ.get("SHAREPOINT_SITE_PATH"),
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


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_access_token()}"}


def _get_site_and_drive() -> tuple[str, str] | tuple[None, None]:
    """Vrátí (site_id, drive_id), s cachováním (mění se jen výjimečně)."""
    if _site_cache["site_id"] and _site_cache["drive_id"]:
        return _site_cache["site_id"], _site_cache["drive_id"]

    hostname = os.environ["SHAREPOINT_SITE_HOSTNAME"]
    site_path = os.environ["SHAREPOINT_SITE_PATH"]

    resp = httpx.get(f"{GRAPH_BASE}/sites/{hostname}:{site_path}", headers=_headers(), timeout=15.0)
    if resp.status_code >= 400:
        logger.error("SharePoint: GET site selhalo (%s): %s", resp.status_code, resp.text)
    resp.raise_for_status()
    site_id = resp.json()["id"]

    resp = httpx.get(f"{GRAPH_BASE}/sites/{site_id}/drive", headers=_headers(), timeout=15.0)
    if resp.status_code >= 400:
        logger.error("SharePoint: GET drive selhalo (%s): %s", resp.status_code, resp.text)
    resp.raise_for_status()
    drive_id = resp.json()["id"]

    _site_cache["site_id"] = site_id
    _site_cache["drive_id"] = drive_id
    return site_id, drive_id


def _get_zakazky_folder_id(drive_id: str) -> str:
    """Najde ID nadřazené složky (např. '03_Zakázky'), s cachováním."""
    if _site_cache["zakazky_folder_id"]:
        return _site_cache["zakazky_folder_id"]

    folder_name = os.environ.get("SHAREPOINT_ZAKAZKY_FOLDER", "03_Zakázky")
    resp = httpx.get(f"{GRAPH_BASE}/drives/{drive_id}/root:/{folder_name}", headers=_headers(), timeout=15.0)
    if resp.status_code >= 400:
        logger.error("SharePoint: GET /03_Zakázky selhalo (%s): %s", resp.status_code, resp.text)
    resp.raise_for_status()
    folder_id = resp.json()["id"]
    _site_cache["zakazky_folder_id"] = folder_id
    return folder_id


def create_deal_folder(folder_name: str) -> dict | None:
    """
    Vytvoří novou složku zakázky (uvnitř "03_Zakázky") se 6 podsložkami
    podle šablony. Vrací {"folder_id", "web_url", "drive_id",
    "nabidka_subfolder_id", "fakturace_subfolder_id"} nebo None při
    selhání/nenakonfigurování.
    """
    if not is_configured():
        logger.info("SharePoint není nakonfigurován - složka '%s' se nevytváří", folder_name)
        return None

    try:
        site_id, drive_id = _get_site_and_drive()
        parent_id = _get_zakazky_folder_id(drive_id)

        resp = httpx.post(
            f"{GRAPH_BASE}/drives/{drive_id}/items/{parent_id}/children",
            json={
                "name": folder_name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "rename",
            },
            headers={**_headers(), "Content-Type": "application/json"},
            timeout=15.0,
        )
        if resp.status_code >= 400:
            logger.error("SharePoint: vytvoření složky selhalo (%s): %s", resp.status_code, resp.text)
        resp.raise_for_status()
        folder_data = resp.json()
        folder_id = folder_data["id"]
        web_url = folder_data.get("webUrl")

        subfolder_ids = {}
        for subfolder_name in SUBFOLDERS:
            sub_resp = httpx.post(
                f"{GRAPH_BASE}/drives/{drive_id}/items/{folder_id}/children",
                json={
                    "name": subfolder_name,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "rename",
                },
                headers={**_headers(), "Content-Type": "application/json"},
                timeout=15.0,
            )
            if sub_resp.status_code >= 400:
                logger.error(
                    "SharePoint: vytvoření podsložky '%s' selhalo (%s): %s",
                    subfolder_name,
                    sub_resp.status_code,
                    sub_resp.text,
                )
                continue
            subfolder_ids[subfolder_name] = sub_resp.json()["id"]

        logger.info("SharePoint: složka '%s' vytvořena (ID %s)", folder_name, folder_id)
        return {
            "folder_id": folder_id,
            "web_url": web_url,
            "drive_id": drive_id,
            "poptavka_subfolder_id": subfolder_ids.get("01_Poptávka"),
            "nabidka_subfolder_id": subfolder_ids.get("02_Nabídka"),
            "fakturace_subfolder_id": subfolder_ids.get("04_Fakturace"),
        }
    except Exception:
        logger.exception("SharePoint: create_deal_folder selhalo pro '%s'", folder_name)
        return None


def upload_file_to_folder(drive_id: str, folder_id: str, filename: str, content_bytes: bytes) -> bool:
    """Nahraje soubor do konkrétní složky na SharePointu. Vrací True/False."""
    if not is_configured() or not drive_id or not folder_id:
        return False
    try:
        resp = httpx.put(
            f"{GRAPH_BASE}/drives/{drive_id}/items/{folder_id}:/{filename}:/content",
            content=content_bytes,
            headers={**_headers(), "Content-Type": "application/octet-stream"},
            timeout=30.0,
        )
        if resp.status_code >= 400:
            logger.error("SharePoint: nahrání souboru '%s' selhalo (%s): %s", filename, resp.status_code, resp.text)
        resp.raise_for_status()
        logger.info("SharePoint: soubor '%s' nahrán do složky %s", filename, folder_id)
        return True
    except Exception:
        logger.exception("SharePoint: upload_file_to_folder selhalo pro '%s'", filename)
        return False
