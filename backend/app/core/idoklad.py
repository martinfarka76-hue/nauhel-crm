"""
Integrace s iDokladem (vystavování skutečných daňových dokladů). OAuth2
"client credentials" flow - žádná interakce uživatele není potřeba.

Vyžaduje proměnné prostředí IDOKLAD_CLIENT_ID a IDOKLAD_CLIENT_SECRET.
Pokud nejsou nastavené, veškerá volání se tiše přeskočí (jen zaloguje
info) - ať appka funguje i před dokončením nastavení, stejně jako
u MS Graph integrace.

POZNÁMKA: přesné názvy polí u položek faktury (zejména DPH) nejsou
stoprocentně ověřené z oficiální dokumentace (ta je jen jako interaktivní
JS aplikace, ne staticky čitelná). Ladí se podle skutečných odpovědí
API při prvním ostrém testu.
"""
import os
import time
import logging
import httpx

logger = logging.getLogger("nauhel_crm.idoklad")

_token_cache = {"access_token": None, "expires_at": 0.0}

TOKEN_URL = "https://identity.idoklad.cz/server/connect/token"
API_BASE = "https://api.idoklad.cz/v3"


def is_configured() -> bool:
    return bool(os.environ.get("IDOKLAD_CLIENT_ID")) and bool(os.environ.get("IDOKLAD_CLIENT_SECRET"))


def _get_access_token() -> str:
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["access_token"]

    client_id = os.environ["IDOKLAD_CLIENT_ID"]
    client_secret = os.environ["IDOKLAD_CLIENT_SECRET"]

    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "idoklad_api",
    }
    resp = httpx.post(TOKEN_URL, data=data, timeout=15.0)
    resp.raise_for_status()
    token_data = resp.json()
    _token_cache["access_token"] = token_data["access_token"]
    _token_cache["expires_at"] = now + token_data.get("expires_in", 1800)
    logger.info("iDoklad: nový access token získán")
    return _token_cache["access_token"]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }


def find_or_create_contact(ico: str, name: str, address: str = None) -> int | None:
    """
    Najde odběratele v iDokladu podle IČO. Pokud neexistuje, vytvoří ho.
    Vrací interní ID kontaktu v iDokladu (int), nebo None při selhání.
    """
    if not is_configured():
        logger.info("iDoklad není nakonfigurován - přeskakuji find_or_create_contact")
        return None

    try:
        # Hledání podle IČO
        if ico:
            resp = httpx.get(
                f"{API_BASE}/Contacts",
                params={"filter": f"IdentificationNumber~eq~{ico}"},
                headers=_headers(),
                timeout=15.0,
            )
            if resp.status_code >= 400:
                logger.error("iDoklad: GET /Contacts selhalo (%s): %s", resp.status_code, resp.text)
            resp.raise_for_status()
            result = resp.json()
            data_section = result.get("Data")
            if isinstance(data_section, dict):
                items = data_section.get("Items", [])
            elif isinstance(data_section, list):
                items = data_section
            else:
                items = result.get("Items") or []
            if items:
                contact_id = items[0].get("Id")
                logger.info("iDoklad: nalezen existující kontakt %s pro IČO %s", contact_id, ico)
                return contact_id

        # Nenalezeno (nebo bez IČO) - vytvoř nový kontakt
        payload = {"CompanyName": name, "CountryId": 1}  # 1 = Česká republika
        if ico:
            payload["IdentificationNumber"] = ico
        if address:
            payload["Street"] = address

        resp = httpx.post(f"{API_BASE}/Contacts", json=payload, headers=_headers(), timeout=15.0)
        if resp.status_code >= 400:
            logger.error("iDoklad: POST /Contacts selhalo (%s): %s", resp.status_code, resp.text)
        resp.raise_for_status()
        resp_json = resp.json()
        contact_obj = resp_json.get("Data") if isinstance(resp_json.get("Data"), dict) else resp_json
        contact_id = contact_obj.get("Id")
        logger.info("iDoklad: vytvořen nový kontakt %s (%s)", contact_id, name)
        return contact_id
    except Exception:
        logger.exception("iDoklad: find_or_create_contact selhalo pro '%s' (IČO %s)", name, ico)
        return None


def create_issued_invoice(
    purchaser_id: int,
    item_name: str,
    amount: float,
    vat_rate: float,
    is_advance_invoice: bool = False,
) -> dict | None:
    """
    Vytvoří vydanou fakturu v iDokladu s jednou položkou (částka je
    včetně DPH - IsVatMovement/PriceType se řeší podle konkrétní odpovědi
    API při testování). Vrací {"id", "number", "pdf_url"} nebo None při
    selhání/nenakonfigurování.
    """
    if not is_configured():
        logger.info("iDoklad není nakonfigurován - faktura se nevystavuje (%s)", item_name)
        return None

    try:
        import datetime as _dt

        today = _dt.date.today()
        due_date = today + _dt.timedelta(days=14)

        # iDoklad vyžaduje kompletně vyplněný objekt faktury (bez automatických
        # výchozích hodnot pro spoustu detailních polí) - proto si nejdřív
        # stáhneme "výchozí" šablonu z účtu (měna, číselná řada, způsob platby...)
        # a jen v ní přepíšeme to, co potřebujeme.
        default_resp = httpx.get(f"{API_BASE}/IssuedInvoices/Default", headers=_headers(), timeout=15.0)
        if default_resp.status_code >= 400:
            logger.error(
                "iDoklad: GET /IssuedInvoices/Default selhalo (%s): %s",
                default_resp.status_code,
                default_resp.text,
            )
        default_resp.raise_for_status()
        default_json = default_resp.json()
        payload = default_json.get("Data") if isinstance(default_json.get("Data"), dict) else default_json

        vat_rate_percent = round(float(vat_rate) * 100)

        # Vezmi výchozí šablonu položky (pokud existuje), jinak prázdný slovník,
        # a přepiš jen to, co potřebujeme - zachová ostatní povinná pole se
        # svými výchozími hodnotami (DiscountPercentage, IsTaxMovement, ...)
        default_items = payload.get("Items") or []
        item_template = dict(default_items[0]) if default_items else {}
        item_template.update(
            {
                "Name": item_name,
                "Amount": 1,
                "UnitPrice": amount,
                "PriceType": 1,  # 1 = cena s DPH (dle konvence iDoklad - ověřit při testu)
                "VatRatePercent": vat_rate_percent,
            }
        )

        payload.update(
            {
                "PurchaserId": purchaser_id,
                "Description": item_name,
                "DateOfIssue": today.isoformat(),
                "DateOfTaxing": today.isoformat(),
                "DateOfMaturity": due_date.isoformat(),
                "Items": [item_template],
            }
        )
        resp = httpx.post(f"{API_BASE}/IssuedInvoices", json=payload, headers=_headers(), timeout=15.0)
        if resp.status_code >= 400:
            logger.error("iDoklad: POST /IssuedInvoices selhalo (%s): %s", resp.status_code, resp.text)
        resp.raise_for_status()
        resp_json = resp.json()
        data = resp_json.get("Data") if isinstance(resp_json.get("Data"), dict) else resp_json
        invoice_id = data.get("Id")
        invoice_number = data.get("DocumentNumber") or data.get("Number")
        pdf_url = f"{API_BASE}/IssuedInvoices/{invoice_id}/GetPdf" if invoice_id else None
        logger.info("iDoklad: faktura vystavena - ID %s, číslo %s", invoice_id, invoice_number)
        return {"id": invoice_id, "number": invoice_number, "pdf_url": pdf_url}
    except Exception:
        logger.exception("iDoklad: create_issued_invoice selhalo (%s, %.2f Kč)", item_name, amount)
        return None
