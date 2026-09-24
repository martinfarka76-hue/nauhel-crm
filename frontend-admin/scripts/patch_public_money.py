path = "app/n/[token]/page.js"
old = '''function formatMoney(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("cs-CZ") + " Kč";
}'''
new = '''function formatMoney(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("cs-CZ", { maximumFractionDigits: 0 }) + " Kč";
}'''

with open(path) as f:
    content = f.read()
count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Opraveno")
