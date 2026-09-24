path = "app/n/[token]/page.js"
with open(path) as f:
    content = f.read()

old = 'body: JSON.stringify({ confirmed_by_name: confirmName.trim(), agreed_to_terms: true }),'
new = 'body: JSON.stringify({ confirmed_by_name: confirmName.trim(), agreed_to_terms: true, vop_url: VOP_URL }),'

count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Opraveno")
