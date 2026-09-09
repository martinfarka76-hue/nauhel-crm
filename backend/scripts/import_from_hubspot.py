"""
Jednorázový (ale opakovaně spustitelný) import dat z HubSpotu do NAUHEL CRM.

Stahuje Firmy, Kontakty, Dealy a Poznámky přímo z HubSpot REST API v3
(ne přes MCP konektor, který má denní limit dotazů) a vytváří odpovídající
záznamy přímo v databázi - BEZ spouštění normálních vedlejších efektů
(žádný e-mail zákazníkovi, žádná nová SharePoint složka), protože se
zapisuje rovnou přes SQLAlchemy session, ne přes transition endpoint.

Použití:
    python -m scripts.import_from_hubspot --dry-run   # jen vypíše, nic neuloží
    python -m scripts.import_from_hubspot              # skutečný import

Vyžaduje proměnnou prostředí HUBSPOT_API_TOKEN (private app token, "pat-...").
"""
import os
import sys
import uuid as uuid_module
import argparse
from datetime import datetime, date

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.company import Company
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.deal_note import DealNote
from app.models.user import User
from app.models.enums import DealStatus

HUBSPOT_API_TOKEN = os.environ.get("HUBSPOT_API_TOKEN")
HUBSPOT_BASE = "https://api.hubapi.com"

# Mapování HubSpot dealstage -> náš DealStatus (odsouhlaseno s uživatelem)
STAGE_MAP = {
    "appointmentscheduled": DealStatus.LEAD,
    "qualifiedtobuy": DealStatus.KVALIFIKOVANY_LEAD,
    "presentationscheduled": DealStatus.NABIDKA,
    "decisionmakerboughtin": DealStatus.OBJEDNAVKA,
    "contractsent": DealStatus.ZALOHOVA_FAKTURA,
    "closedwon": DealStatus.FAKTUROVANO,
    "closedlost": DealStatus.ZTRACENO,
}

# Mapování HubSpot owner ID -> email uživatele v naší databázi
OWNER_EMAIL_MAP = {
    "30539968": "farka@nauhel.cz",       # Martin Farka
    "30721266": "sindelar@nauhel.cz",    # Jiří Šindelář - OVĚŘIT přesný email!
}


def hubspot_get(path: str, params: dict) -> dict:
    headers = {"Authorization": f"Bearer {HUBSPOT_API_TOKEN}"}
    resp = httpx.get(f"{HUBSPOT_BASE}{path}", headers=headers, params=params, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


def fetch_all(path: str, properties: list[str], extra_params: dict | None = None) -> list[dict]:
    """Stáhne VŠECHNY záznamy daného typu (stránkuje přes 'after' kurzor)."""
    results = []
    after = None
    params = {"limit": 100, "properties": ",".join(properties)}
    if extra_params:
        params.update(extra_params)
    while True:
        if after:
            params["after"] = after
        data = hubspot_get(path, params)
        results.extend(data.get("results", []))
        paging = data.get("paging", {})
        after = paging.get("next", {}).get("after")
        if not after:
            break
    return results


def fetch_deal_associations(deal_id: str, to_object_type: str) -> list[str]:
    """Vrátí seznam ID asociovaných objektů (company/contact/note) pro daný Deal.
    HubSpot vrací toObjectId jako číslo, ale ostatní objekty jsou klíčované
    jako string (podle /objects/{type} endpointu) - proto vždy str()."""
    data = hubspot_get(f"/crm/v4/objects/deals/{deal_id}/associations/{to_object_type}", {})
    return [str(r["toObjectId"]) for r in data.get("results", [])]


def hs_timestamp_to_date(iso_str: str | None) -> date | None:
    if not iso_str:
        return None
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).date()


def hs_timestamp_to_datetime(iso_str: str | None) -> datetime | None:
    if not iso_str:
        return None
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).replace(tzinfo=None)


def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Jen vypsat, co by se importovalo, nic neukládat")
    args = parser.parse_args()

    if not HUBSPOT_API_TOKEN:
        print("CHYBA: HUBSPOT_API_TOKEN není nastavený v prostředí.")
        sys.exit(1)

    print("Stahuji data z HubSpotu...")
    hs_companies = fetch_all("/crm/v3/objects/companies", ["name", "domain", "address", "city"])
    hs_contacts = fetch_all("/crm/v3/objects/contacts", ["firstname", "lastname", "email", "phone"])
    hs_deals = fetch_all(
        "/crm/v3/objects/deals",
        ["dealname", "dealstage", "amount", "closedate", "createdate", "hubspot_owner_id"],
    )
    hs_notes = fetch_all("/crm/v3/objects/notes", ["hs_note_body", "hs_timestamp"])
    print(f"  {len(hs_companies)} firem, {len(hs_contacts)} kontaktů, {len(hs_deals)} dealů, {len(hs_notes)} poznámek")

    hs_companies_by_id = {c["id"]: c for c in hs_companies}
    hs_contacts_by_id = {c["id"]: c for c in hs_contacts}
    hs_notes_by_id = {n["id"]: n for n in hs_notes}

    db = SessionLocal()

    # --- Uživatelé (mapování owner -> User.id v naší DB) ---
    users_by_email = {u.email: u for u in db.query(User).all()}
    owner_to_user_id = {}
    for hs_owner_id, email in OWNER_EMAIL_MAP.items():
        user = users_by_email.get(email)
        if user:
            owner_to_user_id[hs_owner_id] = user.id
        else:
            print(f"  VAROVÁNÍ: uživatel s emailem {email} nenalezen v DB, dealy s tímto vlastníkem budou bez vlastníka")

    # --- Existující firmy v naší DB (pro deduplikaci) ---
    existing_companies = db.query(Company).all()
    companies_by_norm_name = {normalize_name(c.name): c for c in existing_companies}

    # mapování: HubSpot company ID -> naše Company (vytvoří se za běhu)
    hs_company_id_to_our_company = {}
    new_companies_count = 0

    for hs_id, hs_c in hs_companies_by_id.items():
        props = hs_c["properties"]
        name = props.get("name") or f"Firma bez názvu ({hs_id})"
        norm = normalize_name(name)
        if norm in companies_by_norm_name:
            hs_company_id_to_our_company[hs_id] = companies_by_norm_name[norm]
            continue
        new_company = Company(
            name=name,
            website=props.get("domain"),
            address=", ".join(filter(None, [props.get("address"), props.get("city")])) or None,
        )
        hs_company_id_to_our_company[hs_id] = new_company
        companies_by_norm_name[norm] = new_company
        new_companies_count += 1
        if not args.dry_run:
            db.add(new_company)

    # --- Existující kontakty (pro deduplikaci podle emailu) ---
    existing_contacts = db.query(Contact).all()
    contacts_by_email = {c.email.lower(): c for c in existing_contacts if c.email}

    hs_contact_id_to_our_contact = {}
    new_contacts_count = 0

    for hs_id, hs_c in hs_contacts_by_id.items():
        props = hs_c["properties"]
        email = (props.get("email") or "").lower().strip()
        first_name = props.get("firstname") or "?"
        last_name = props.get("lastname") or "?"
        if email and email in contacts_by_email:
            hs_contact_id_to_our_contact[hs_id] = contacts_by_email[email]
            continue
        # Kontakt se přiřadí k první nalezené asociované firmě (dopočítá se níž při zpracování Dealů)
        hs_contact_id_to_our_contact[hs_id] = Contact(
            first_name=first_name,
            last_name=last_name,
            email=props.get("email"),
            phone=props.get("phone"),
        )
        if email:
            contacts_by_email[email] = hs_contact_id_to_our_contact[hs_id]
        new_contacts_count += 1

    # --- Dealy ---
    print("Zpracovávám dealy a jejich asociace (může chvíli trvat)...")
    deals_to_create = []
    notes_to_create = []
    skipped_stage = 0
    contacts_needing_company = set()

    for hs_deal in hs_deals:
        deal_id = hs_deal["id"]
        props = hs_deal["properties"]
        stage = props.get("dealstage")
        our_status = STAGE_MAP.get(stage)
        if not our_status:
            print(f"  VAROVÁNÍ: neznámý stav '{stage}' u dealu '{props.get('dealname')}', přeskakuji")
            skipped_stage += 1
            continue

        company_ids = fetch_deal_associations(deal_id, "companies")
        contact_ids = fetch_deal_associations(deal_id, "contacts")
        note_ids = fetch_deal_associations(deal_id, "notes")

        our_company = None
        if company_ids:
            our_company = hs_company_id_to_our_company.get(company_ids[0])
        if not our_company:
            # Deal bez napojené firmy - vytvoříme "firmu" podle názvu dealu, ať má Deal kam patřit
            fallback_name = props.get("dealname") or f"Neznámá firma ({deal_id})"
            norm = normalize_name(fallback_name)
            our_company = companies_by_norm_name.get(norm)
            if not our_company:
                our_company = Company(name=fallback_name)
                companies_by_norm_name[norm] = our_company
                new_companies_count += 1

        our_contact = None
        if contact_ids:
            our_contact = hs_contact_id_to_our_contact.get(contact_ids[0])
            if our_contact is not None:
                contacts_needing_company.add(id(our_contact))
                our_contact.company = our_company

        owner_id = owner_to_user_id.get(props.get("hubspot_owner_id"))

        deal = Deal(
            id=uuid_module.uuid4(),
            name=props.get("dealname") or "Bez názvu",
            status=our_status,
            price=float(props["amount"]) if props.get("amount") else None,
            expected_close_date=hs_timestamp_to_date(props.get("closedate")),
            owner_user_id=owner_id,
            created_at=hs_timestamp_to_datetime(props.get("createdate")) or datetime.utcnow(),
        )
        deal.company = our_company
        if our_contact:
            deal.contact = our_contact

        deals_to_create.append(deal)

        for note_id in note_ids:
            hs_note = hs_notes_by_id.get(note_id)
            if not hs_note:
                continue
            body = hs_note["properties"].get("hs_note_body")
            if not body:
                continue
            note = DealNote(
                content=body,
                author_user_id=owner_id,
                deal_id=deal.id,
                created_at=hs_timestamp_to_datetime(hs_note["properties"].get("hs_timestamp")) or datetime.utcnow(),
            )
            notes_to_create.append(note)

    print()
    print("=" * 60)
    print("SOUHRN IMPORTU")
    print("=" * 60)
    print(f"Nové firmy:    {new_companies_count}")
    print(f"Nové kontakty: {new_contacts_count}")
    print(f"Dealy:         {len(deals_to_create)} (přeskočeno kvůli neznámému stavu: {skipped_stage})")
    print(f"Poznámky:      {len(notes_to_create)}")
    print()
    print("Rozpad dealů podle stavu:")
    from collections import Counter
    status_counts = Counter(d.status.value for d in deals_to_create)
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    if args.dry_run:
        print()
        print("DRY-RUN - nic nebylo uloženo. Spusť bez --dry-run pro skutečný import.")
        db.close()
        return

    print()
    print("Ukládám do databáze...")
    for company in companies_by_norm_name.values():
        db.add(company)
    for contact in hs_contact_id_to_our_contact.values():
        if contact.company is not None:
            db.add(contact)
    for deal in deals_to_create:
        db.add(deal)
    db.flush()  # zapíše Dealy do DB (v rámci transakce) dřív, než přidáme Poznámky - jinak by FK selhalo
    for note in notes_to_create:
        db.add(note)
    db.commit()
    print("Hotovo.")
    db.close()


if __name__ == "__main__":
    main()
