path = "app/globals.css"
with open(path) as f:
    content = f.read()

old = '''  .page-title {
    font-size: 19px;
  }
}'''
new = '''  .page-title {
    font-size: 19px;
  }

  .followup-banner {
    display: none;
  }
}'''

count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x (ocekavano 1x)")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Patch zapsan uspesne")
