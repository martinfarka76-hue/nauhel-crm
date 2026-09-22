path = "app/routers/deal_attachment.py"
with open(path) as f:
    content = f.read()

old = "    sync_attachment_to_sharepoint(db, deal, original_name, content)"
new = "    sync_attachment_to_sharepoint(db, deal, attachment, content)"

count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Router opraven")
