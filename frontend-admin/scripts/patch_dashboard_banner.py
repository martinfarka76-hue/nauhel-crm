path = "app/page.js"
with open(path) as f:
    content = f.read()

patches = []

# 1) Zpet zobrazovat i v kanbanu (odstranit viewMode podminku)
old1 = '{!loading && viewMode !== "kanban" && (() => {'
new1 = '{!loading && (() => {'
patches.append((old1, new1))

# 2) Pridat className pro CSS skryti na mobilu
old2 = '''        return (
          <div
            className="card"
            style={{
              marginBottom: 12,
              flexShrink: 0,
              padding: "8px 12px",
              background: "#fdf3ec",
              borderColor: "var(--ember-500)",
            }}
          >'''
new2 = '''        return (
          <div
            className="card followup-banner"
            style={{
              marginBottom: 12,
              flexShrink: 0,
              padding: "8px 12px",
              background: "#fdf3ec",
              borderColor: "var(--ember-500)",
            }}
          >'''
patches.append((old2, new2))

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
    print("Vsechny 2 patche zapsany uspesne")
else:
    print("NIC nebylo zapsano kvuli chybe vyse")
