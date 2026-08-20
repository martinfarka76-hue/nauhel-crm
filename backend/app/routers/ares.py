import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/ares", tags=["ares"])

ARES_BASE_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty"


@router.get("/{ico}")
def lookup_ico(ico: str):
    """
    Vyhledá firmu podle IČO ve veřejném registru ARES (ares.gov.cz).
    Vrací název, sídlo a IČO. DIČ ARES přímo neposkytuje - odhad "CZ{ico}"
    je jen orientační (platí pro většinu, ale ne pro všechny subjekty),
    proto se posílá jako dic_guess, ne jako jistý údaj.
    """
    try:
        resp = httpx.get(f"{ARES_BASE_URL}/{ico}", timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Registr ARES je momentálně nedostupný, zkus to prosím později.")

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="IČO nebylo v registru ARES nalezeno.")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Chyba při komunikaci s registrem ARES.")

    data = resp.json()
    sidlo = data.get("sidlo", {})
    found_ico = data.get("ico")

    return {
        "ico": found_ico,
        "name": data.get("obchodniJmeno"),
        "address": sidlo.get("textovaAdresa"),
        "dic_guess": f"CZ{found_ico}" if found_ico else None,
    }
