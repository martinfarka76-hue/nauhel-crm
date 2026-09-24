path = "app/models/document.py"
with open(path) as f:
    content = f.read()

old = '''    # Explicitní souhlas s Všeobecnými obchodními podmínkami při potvrzení
    # objednávky - právně relevantní záznam, oddělený od samotného potvrzení
    agreed_to_terms = Column(Boolean, nullable=False, default=False)'''
new = '''    # Explicitní souhlas s Všeobecnými obchodními podmínkami při potvrzení
    # objednávky - právně relevantní záznam, oddělený od samotného potvrzení
    agreed_to_terms = Column(Boolean, nullable=False, default=False)

    # Dukazni zaznam pro pripad sporu/soudniho reseni - IP adresa v okamziku
    # potvrzeni, a otisk (SHA-256) + ulozeny soubor presneho zneni VOP, jake
    # bylo zobrazeno v dobe potvrzeni (odkaz na VOP muze casem ukazovat na
    # jiny obsah, snapshot dokazuje presne to, co zakaznik tehdy odsouhlasil).
    confirmation_ip_address = Column(String(45), nullable=True)
    vop_snapshot_filename = Column(String(255), nullable=True)
    vop_snapshot_sha256 = Column(String(64), nullable=True)'''

count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Document model opraven")
