import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ares", tags=["ares"])

ARES_BASE_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty"


@router.get("/{ico}")
def lookup_ico(ico: str, current_user: User = Depends(get_current_user)):
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


class AresNameSearchRequest(BaseModel):
    name: str


@router.post("/search")
def search_by_name(payload: AresNameSearchRequest, current_user: User = Depends(get_current_user)):
    """
    Vyhledá firmy v registru ARES podle (části) názvu - na rozdíl od
    vyhledání podle IČO může vrátit VÍCE shod, proto se vrací seznam
    kandidátů k ručnímu výběru, ne jeden jistý výsledek. Použití: doplnění
    chybějícího IČO u firem naimportovaných odjinud (např. z HubSpotu).
    """
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Zadej název firmy.")

    try:
        resp = httpx.post(
            f"{ARES_BASE_URL}/vyhledat",
            json={"obchodniJmeno": name, "pocet": 10},
            timeout=10.0,
        )
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Registr ARES je momentálně nedostupný, zkus to prosím později.")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Chyba při komunikaci s registrem ARES.")

    data = resp.json()
    subjects = data.get("ekonomickeSubjekty", [])

    results = []
    for s in subjects:
        sidlo = s.get("sidlo", {})
        found_ico = s.get("ico")
        results.append({
            "ico": found_ico,
            "name": s.get("obchodniJmeno"),
            "address": sidlo.get("textovaAdresa"),
            "dic_guess": f"CZ{found_ico}" if found_ico else None,
        })

    return {"results": results}
