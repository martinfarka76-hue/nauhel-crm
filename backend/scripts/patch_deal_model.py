path = "app/models/deal.py"
with open(path) as f:
    content = f.read()

old = "    sharepoint_subfolder_realizace_id = Column(String(255), nullable=True)"
new = '''    sharepoint_subfolder_realizace_id = Column(String(255), nullable=True)
    sharepoint_subfolder_smlouvy_id = Column(String(255), nullable=True)'''

count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Deal model opraven")
