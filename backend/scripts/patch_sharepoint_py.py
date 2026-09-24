path = "app/core/sharepoint.py"
with open(path) as f:
    content = f.read()

old = '''            "poptavka_subfolder_id": subfolder_ids.get("01_Poptávka"),
            "nabidka_subfolder_id": subfolder_ids.get("02_Nabídka"),
            "realizace_subfolder_id": subfolder_ids.get("03_Realizace"),
            "fakturace_subfolder_id": subfolder_ids.get("04_Fakturace"),
        }'''
new = '''            "poptavka_subfolder_id": subfolder_ids.get("01_Poptávka"),
            "nabidka_subfolder_id": subfolder_ids.get("02_Nabídka"),
            "realizace_subfolder_id": subfolder_ids.get("03_Realizace"),
            "fakturace_subfolder_id": subfolder_ids.get("04_Fakturace"),
            "smlouvy_subfolder_id": subfolder_ids.get("06_Smlouvy a specifikace"),
        }'''

count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("sharepoint.py opraveno")
