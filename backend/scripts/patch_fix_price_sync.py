path = "app/routers/calculation.py"
with open(path) as f:
    content = f.read()

old = '''    calculation.is_active = True
    db.commit()
    db.refresh(calculation)
    return calculation'''
new = '''    calculation.is_active = True
    return recompute_calculation_totals(db, calculation)'''

count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Opraveno - deal.price se ted spravne synchronizuje")
