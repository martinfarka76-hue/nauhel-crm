path = "app/core/scheduler.py"
with open(path) as f:
    content = f.read()

patches = []

# 1) Import or_, func
old1 = "from sqlalchemy.orm import Session"
new1 = "from sqlalchemy import or_, func\nfrom sqlalchemy.orm import Session"
patches.append((old1, new1))

# 2) Podminka - notifikovat, pokud jeste nikdy NEBO ne uz dnes
old2 = '''        candidates = (
            db.query(Deal)
            .filter(
                Deal.next_contact_date.isnot(None),
                Deal.next_contact_date <= today + timedelta(days=1),
                Deal.next_contact_notified_at.is_(None),
                Deal.status.notin_(TERMINAL_STATUSES),
            )
            .all()
        )'''
new2 = '''        candidates = (
            db.query(Deal)
            .filter(
                Deal.next_contact_date.isnot(None),
                Deal.next_contact_date <= today + timedelta(days=1),
                or_(
                    Deal.next_contact_notified_at.is_(None),
                    func.date(Deal.next_contact_notified_at) < today,
                ),
                Deal.status.notin_(TERMINAL_STATUSES),
            )
            .all()
        )'''
patches.append((old2, new2))

# 3) Docstring update
old3 = '''    Denní kontrola termínů dalšího kontaktu (next_contact_date) u Dealů.
    Upozornění se vytvoří už DEN PŘED termínem, ať má obchodník čas se
    připravit - a pak dál, dokud termín trvá/je po termínu. Deal nesmí být
    v koncovém stavu (Fakturováno/Ztraceno) a notifikace pro tenhle termín
    ještě nesmí být vytvořena (next_contact_notified_at je NULL).
    """'''
new3 = '''    Denní kontrola termínů dalšího kontaktu (next_contact_date) u Dealů.
    Upozornění se vytvoří už DEN PŘED termínem, ať má obchodník čas se
    připravit - a pak OPAKOVANĚ KAŽDÝ DEN, dokud termín zůstává po
    splatnosti a nikdo nezmáčkl "Hotovo" (next_contact_date se nezměnil).
    Deal nesmí být v koncovém stavu (Fakturováno/Ztraceno). Notifikace se
    pro daný den vytvoří jen jednou (next_contact_notified_at hlídá "dnes
    už bylo").
    """'''
patches.append((old3, new3))

ok = True
for i, (old, new) in enumerate(patches):
    count = content.count(old)
    if count != 1:
        print(f"CHYBA patch {i+1}: nalezeno {count}x (ocekavano 1x)")
        ok = False
    else:
        content = content.replace(old, new)

if ok:
    with open(path, 'w') as f:
        f.write(content)
    print("Vsechny 3 patche zapsany uspesne")
else:
    print("NIC nebylo zapsano kvuli chybe vyse")
