path = "app/core/deal_folder.py"
with open(path) as f:
    content = f.read()

old = '''def _sanitize_filename_part(text: str) -> str:
    """Odstraní znaky nevhodné pro název souboru na SharePointu/Windows."""
    return re.sub(r'[\\\\/:*?"<>|]', "", text or "").strip()'''
new = '''def _sanitize_filename_part(text: str) -> str:
    """Odstraní znaky nevhodné pro název souboru na SharePointu/Windows.
    Windows/SharePoint navíc nepovoluje, aby název souboru/složky KONČIL
    tečkou nebo mezerou (typicky se stává u firem s "s.r.o." na konci
    názvu) - proto se to na konci ještě ořízne."""
    cleaned = re.sub(r'[\\\\/:*?"<>|]', "", text or "").strip()
    return cleaned.rstrip(". ")'''

count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x (ocekavano 1x)")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Patch zapsan uspesne")
