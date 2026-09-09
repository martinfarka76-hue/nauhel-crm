"""
Jednorázový čistící skript po importu z HubSpotu.
"""
import os
import sys
import argparse
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.company import Company
from app.models.contact import Contact
from app.models.deal import Deal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()

    deals = db.query(Deal).all()
    fallback_deals = [d for d in deals if d.company and d.company.name == d.name]

    print(f"Nalezeno {len(fallback_deals)} dealu s nahradni firmou.")

    groups = defaultdict(list)
    for d in fallback_deals:
        key = d.contact_id if d.contact_id else f"no-contact-{d.company_id}"
        groups[key].append(d)

    merge_count = 0
    rename_count = 0

    for key, group_deals in groups.items():
        companies_in_group = sorted({d.company for d in group_deals}, key=lambda c: c.created_at)
        canonical = companies_in_group[0]
        duplicates = companies_in_group[1:]

        contact = group_deals[0].contact
        if contact and contact.last_name and contact.last_name != "?" and contact.first_name:
            new_name = " ".join(f"{contact.first_name} {contact.last_name}".split())
            if new_name and new_name != canonical.name:
                print(f"  Prejmenovat: '{canonical.name}' -> '{new_name}'")
                if not args.dry_run:
                    canonical.name = new_name
                rename_count += 1

        for d in group_deals:
            if d.company_id != canonical.id:
                print(f"  Deal '{d.name}': firma {d.company.name} -> {canonical.name}")
                if not args.dry_run:
                    d.company = canonical

        for dup in duplicates:
            still_used = db.query(Deal).filter(Deal.company_id == dup.id, Deal.id.notin_([d.id for d in group_deals])).count()
            if still_used > 0:
                print(f"  VAROVANI: firma '{dup.name}' se nesmaze, pouziva ji jeste jiny Deal")
                continue
            print(f"  Mazat duplicitni firmu: '{dup.name}'")
            merge_count += 1
            if not args.dry_run:
                db.delete(dup)

    print()
    print(f"Prejmenovano firem: {rename_count}")
    print(f"Smazano duplicitnich firem: {merge_count}")

    if args.dry_run:
        print("DRY-RUN - nic nebylo ulozeno.")
        db.close()
        return

    db.commit()
    print("Hotovo.")
    db.close()


if __name__ == "__main__":
    main()
