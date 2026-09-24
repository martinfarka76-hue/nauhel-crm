path = "app/core/deal_folder.py"
with open(path) as f:
    content = f.read()

old = "    deal.sharepoint_subfolder_realizace_id = result.get(\"realizace_subfolder_id\")"
new = '''    deal.sharepoint_subfolder_realizace_id = result.get("realizace_subfolder_id")
    deal.sharepoint_subfolder_smlouvy_id = result.get("smlouvy_subfolder_id")'''

count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("deal_folder.py (subfolder) opraveno")
