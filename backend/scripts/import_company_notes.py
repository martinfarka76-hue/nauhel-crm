"""
Doplnkovy import poznamek z HubSpotu, ktere byly napojene na FIRMU (ne na
konkretni Deal) - typicky prospecting poznamky Jiriho primo na firme.
"""
import os
import sys
import argparse
from datetime import datetime

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.company import Company
from app.models.deal import Deal
from app.models.deal_note import DealNote
from app.models.user import User

HUBSPOT_API_TOKEN = os.environ.get("HUBSPOT_API_TOKEN")
HUBSPOT_BASE = "https://api.hubapi.com"

OWNER_EMAIL_MAP = {
    "30539968": "farka@nauhel.cz",
    "30721266": "sindelar@nauhel.cz",
}


def hubspot_get(path, params):
    headers = {"Authorization": f"Bearer {HUBSPOT_API_TOKEN}"}
    resp = httpx.get(f"{HUBSPOT_BASE}{path}", headers=headers, params=params, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


def fetch_all_notes():
    results = []
    after = None
    params = {"limit": 100, "properties": "hs_note_body,hs_timestamp,hubspot_owner_id"}
    while True:
        if after:
            params["after"] = after
        data = hubspot_get("/crm/v3/objects/notes", params)
        results.extend(data.get("results", []))
        paging = data.get("paging", {})
        after = paging.get("next", {}).get("after")
        if not after:
            break
    return results


def fetch_associations(note_id, to_object_type):
    data = hubspot_get(f"/crm/v4/objects/notes/{note_id}/associations/{to_object_type}", {})
    return [str(r["toObjectId"]) for r in data.get("results", [])]


def fetch_company_name(company_id):
    try:
        data = hubspot_get(f"/crm/v3/objects/companies/{company_id}", {"properties": "name"})
        return data.get("properties", {}).get("name")
    except httpx.HTTPStatusError:
        return None


import re

LEGAL_SUFFIXES = ["sro", "spolsro"]


def normalize_name(name):
    n = name.lower()
    n = re.sub(r"[.,]", "", n)
    n = re.sub(r"\s+", "", n)
    for suffix in LEGAL_SUFFIXES:
        if n.endswith(suffix):
            n = n[:-len(suffix)]
            break
    return n


def hs_timestamp_to_datetime(iso_str):
    if not iso_str:
        return None
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).replace(tzinfo=None)


def html_to_text(raw):
    import re
    import html as html_module
    if "<" not in raw:
        return raw
    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|li|h[1-6])\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_module.unescape(text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join([l for l in lines if l]).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not HUBSPOT_API_TOKEN:
        print("CHYBA: HUBSPOT_API_TOKEN neni nastaveny v prostredi.")
        sys.exit(1)

    db = SessionLocal()
    users_by_email = {u.email: u for u in db.query(User).all()}
    owner_to_user_id = {hs_id: users_by_email[email].id for hs_id, email in OWNER_EMAIL_MAP.items() if email in users_by_email}

    companies = db.query(Company).all()
    companies_by_norm_name = {}
    for c in companies:
        companies_by_norm_name.setdefault(normalize_name(c.name), []).append(c)

    print("Stahuji poznamky z HubSpotu...")
    notes = fetch_all_notes()
    print(f"  {len(notes)} poznamek celkem")

    attached = 0
    skipped_has_deal_already = 0
    skipped_no_company = 0
    skipped_no_match = 0
    skipped_ambiguous = []
    skipped_no_deal = []
    skipped_duplicate = 0

    for note in notes:
        note_id = note["id"]
        props = note["properties"]
        body = props.get("hs_note_body")
        if not body:
            continue

        deal_ids = fetch_associations(note_id, "deals")
        if deal_ids:
            skipped_has_deal_already += 1
            continue

        company_ids = fetch_associations(note_id, "companies")
        if not company_ids:
            skipped_no_company += 1
            continue

        hs_company_name = fetch_company_name(company_ids[0])
        if not hs_company_name:
            skipped_no_company += 1
            continue

        norm = normalize_name(hs_company_name)
        matches = companies_by_norm_name.get(norm)
        if not matches:
            skipped_no_match += 1
            continue

        company = matches[0]
        deals_of_company = db.query(Deal).filter(Deal.company_id == company.id).all()

        if len(deals_of_company) == 0:
            skipped_no_deal.append(hs_company_name)
            continue
        if len(deals_of_company) > 1:
            skipped_ambiguous.append(f"{hs_company_name} ({len(deals_of_company)} dealu)")
            continue

        target_deal = deals_of_company[0]
        content = html_to_text(body)

        existing = db.query(DealNote).filter(DealNote.deal_id == target_deal.id, DealNote.content == content).first()
        if existing:
            skipped_duplicate += 1
            continue

        owner_id = owner_to_user_id.get(props.get("hubspot_owner_id"))
        created_at = hs_timestamp_to_datetime(props.get("hs_timestamp")) or datetime.utcnow()

        print(f"  Priradit '{hs_company_name}' -> Deal '{target_deal.name}': {content[:60]!r}...")
        attached += 1
        if not args.dry_run:
            note_obj = DealNote(deal_id=target_deal.id, author_user_id=owner_id, content=content, created_at=created_at)
            db.add(note_obj)

    print()
    print("=" * 60)
    print("SOUHRN")
    print("=" * 60)
    print(f"Prirazeno k Dealu: {attached}")
    print(f"Preskoceno (uz maji svuj Deal, naimportovano driv): {skipped_has_deal_already}")
    print(f"Preskoceno (poznamka bez Firmy): {skipped_no_company}")
    print(f"Preskoceno (Firma nenalezena v nasi DB): {skipped_no_match}")
    print(f"Preskoceno (duplicita, uz existuje): {skipped_duplicate}")
    print()
    print(f"Firmy BEZ dealu (rucne zkontroluj, {len(skipped_no_deal)}):")
    for name in sorted(set(skipped_no_deal)):
        print(f"  - {name}")
    print()
    print(f"Firmy s VICE dealy (rucne zkontroluj, {len(skipped_ambiguous)}):")
    for name in sorted(set(skipped_ambiguous)):
        print(f"  - {name}")

    if args.dry_run:
        print()
        print("DRY-RUN - nic nebylo ulozeno.")
        db.close()
        return

    db.commit()
    print()
    print("Hotovo.")
    db.close()


if __name__ == "__main__":
    main()
