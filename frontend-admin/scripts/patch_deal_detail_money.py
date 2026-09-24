path = "app/deals/[id]/page.js"
with open(path) as f:
    content = f.read()

patches = []

# 1) Sdilena funkce money()
old1 = '''function money(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("cs-CZ") + " Kč";
}'''
new1 = '''function money(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("cs-CZ", { maximumFractionDigits: 0 }) + " Kč";
}'''
patches.append((old1, new1))

# 2) Radek v dropdownu ceniku partnera
old2 = '{p.wood_type ? ` - ${p.wood_type}` : ""} {p.dimensions ? `(${p.dimensions})` : ""} – {Number(p.service_price_per_m2).toLocaleString("cs-CZ")} Kč/m²'
new2 = '{p.wood_type ? ` - ${p.wood_type}` : ""} {p.dimensions ? `(${p.dimensions})` : ""} – {Number(p.service_price_per_m2).toLocaleString("cs-CZ", { maximumFractionDigits: 0 })} Kč/m²'
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
    print("Vsechny 2 patche zapsany uspesne")
else:
    print("NIC nebylo zapsano kvuli chybe vyse")
