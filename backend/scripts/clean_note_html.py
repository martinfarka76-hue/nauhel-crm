"""
Jednorazovy skript - vycisti HTML znacky z obsahu Poznamek (deal_notes),
ktere vznikly importem z HubSpotu. Zachova odstavce/radky jako nove
radky, jen odstrani samotne znacky a HTML entity.
"""
import os
import re
import sys
import html as html_module
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.deal_note import DealNote


def html_to_text(raw: str) -> str:
    if "<" not in raw:
        return raw

    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|li|h[1-6])\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_module.unescape(text)

    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    notes = db.query(DealNote).all()
    print(f"Nalezeno {len(notes)} poznamek celkem.")

    changed = 0
    for note in notes:
        cleaned = html_to_text(note.content)
        if cleaned != note.content:
            changed += 1
            preview_old = note.content[:60].replace("\n", " ")
            preview_new = cleaned[:60].replace("\n", " ")
            print(f"  '{preview_old}...' -> '{preview_new}...'")
            if not args.dry_run:
                note.content = cleaned

    print()
    print(f"Vycisteno: {changed}")
    print(f"Beze zmeny: {len(notes) - changed}")

    if args.dry_run:
        print("DRY-RUN - nic nebylo ulozeno.")
        db.close()
        return

    db.commit()
    print("Hotovo.")
    db.close()


if __name__ == "__main__":
    main()
