path = "app/schemas/document.py"
with open(path) as f:
    content = f.read()

patches = []

old1 = '''class DocumentConfirmRequest(BaseModel):
    confirmed_by_name: str
    agreed_to_terms: bool'''
new1 = '''class DocumentConfirmRequest(BaseModel):
    confirmed_by_name: str
    agreed_to_terms: bool
    vop_url: Optional[str] = None'''
patches.append((old1, new1))

old2 = '''    confirmed_by_name: Optional[str] = None
    agreed_to_terms: bool = False'''
new2 = '''    confirmed_by_name: Optional[str] = None
    agreed_to_terms: bool = False
    confirmation_ip_address: Optional[str] = None
    vop_snapshot_filename: Optional[str] = None
    vop_snapshot_sha256: Optional[str] = None'''
patches.append((old2, new2))

ok = True
for i, (old, new) in enumerate(patches):
    count = content.count(old)
    if count != 1:
        print(f"CHYBA patch {i+1}: nalezeno {count}x")
        ok = False
    else:
        content = content.replace(old, new)

if ok:
    with open(path, 'w') as f:
        f.write(content)
    print("Document schema opraveno")
else:
    print("NIC nebylo zapsano kvuli chybe vyse")
