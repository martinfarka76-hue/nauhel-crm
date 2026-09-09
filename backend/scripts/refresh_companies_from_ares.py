"""
Jednorázový skript - u všech firem, které MAJÍ vyplněné IČO, ověří a
přepíše název/adresu podle veřejného registru ARES (autoritativní zdroj).
Užitečné po importu z jiného systému, kde název firmy nemusel přesně
odpovídat oficiálnímu obchodnímu jménu.

DIČ se nepřepisuje automaticky (ARES ho přímo neposkytuje, jen odhad
"CZ{ico}") - pokud firma už DIČ má vyplněné, ponechá se beze změny.

Použití:
    python -m scripts.refresh_companies_from_ares --dry-run
    python -m scripts.refresh_companies_from_ares
"""
import os
import sys
import time
import argparse

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.company import Company

ARES_BASE_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty"


def lookup_ico(ico: str) -> dict | None:
    try:
        resp = httpx.get(f"{ARES_BASE_URL}/{ico}", timeout=10.0)
    except httpx.RequestError:
        return None
    if resp.status_code != 200:
        return None
    data = resp.json()
    sidlo = data.get("sidlo", {})
    return {
        "name": data.get("obchodniJmeno"),
        "address": sidlo.get("textovaAdresa"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    companies = db.query(Company).filter(Company.ico.isnot(None), Company.ico != "").all()
    print(f"Nalezeno {len(companies)} firem s vyplněným IČO.")

    updated = 0
    unchanged = 0
    not_found = 0

    for company in companies:
        ares_data = lookup_ico(company.ico)
        time.sleep(0.1)  # slušné tempo dotazů vůči veřejnému registru

        if ares_data is None:
            print(f"  NENALEZENO v ARES: '{company.name}' (IČO {company.ico})")
            not_found += 1
            continue

        changes = []
        if ares_data["name"] and ares_data["name"] != company.name:
            changes.append(f"název '{company.name}' -> '{ares_data['name']}'")
            if not args.dry_run:
                company.name = ares_data["name"]
        if ares_data["address"] and ares_data["address"] != company.address:
            changes.append(f"adresa '{company.address}' -> '{ares_data['address']}'")
            if not args.dry_run:
                company.address = ares_data["address"]

        if changes:
            print(f"  IČO {company.ico}: " + "; ".join(changes))
            updated += 1
        else:
            unchanged += 1

    print()
    print(f"Aktualizováno: {updated}")
    print(f"Beze změny (už sedělo): {unchanged}")
    print(f"Nenalezeno v ARES: {not_found}")

    if args.dry_run:
        print("DRY-RUN - nic nebylo uloženo.")
        db.close()
        return

    db.commit()
    print("Hotovo.")
    db.close()


if __name__ == "__main__":
    main()
