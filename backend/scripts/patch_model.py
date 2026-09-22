path = "app/models/deal_attachment.py"
with open(path) as f:
    content = f.read()

old = '''    content_type = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)'''
new = '''    content_type = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # Kdy se prilohu podarilo nahrat na SharePoint - NULL = jeste nikdy
    # (typicky proto, ze v dobe nahrani jeste neexistovala SharePoint
    # slozka Dealu; viz sync_pending_attachments_for_deal, ktera to
    # dohledava po vytvoreni slozky).
    synced_to_sharepoint_at = Column(DateTime, nullable=True)'''

count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Model opraven")
