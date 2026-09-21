path = "app/reports/page.js"
with open(path) as f:
    content = f.read()

patches = [
    (
        'const RANGE_OPTIONS = [3, 6, 12, 24];',
        'const RANGE_OPTIONS = [3, 6];'
    ),
    (
        'const [rangeMonths, setRangeMonths] = useState(12);',
        'const [rangeMonths, setRangeMonths] = useState(6);'
    ),
]

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
