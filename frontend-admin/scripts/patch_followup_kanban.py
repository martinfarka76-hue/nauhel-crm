path = "app/page.js"
with open(path) as f:
    content = f.read()

old = '''      {!loading && (() => {
        const today = new Date().toISOString().slice(0, 10);
        const threeDaysAhead = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
        const followupDeals = deals'''
new = '''      {!loading && viewMode !== "kanban" && (() => {
        const today = new Date().toISOString().slice(0, 10);
        const threeDaysAhead = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
        const followupDeals = deals'''

count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x (ocekavano 1x)")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Patch zapsan uspesne")
