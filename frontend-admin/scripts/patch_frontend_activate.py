path = "app/deals/[id]/page.js"
with open(path) as f:
    content = f.read()

patches = []

# 1) Nova funkce hned za handleSaveCalc
old1 = '''  function getItemForm(calcId) {
    return itemForms[calcId] || emptyItemForm;
  }'''
new1 = '''  async function handleActivateCalc(calcId) {
    if (
      !window.confirm(
        "Nastavit tuto kalkulaci jako aktivní? Aktuálně aktivní kalkulace se tím deaktivuje (zůstane dostupná v historii)."
      )
    )
      return;
    setError("");
    try {
      const updatedCalc = await api.post(`/calculations/${calcId}/activate`, {});
      setCalculations((prev) =>
        prev.map((c) => {
          if (c.id === calcId) return updatedCalc;
          if (c.deal_id === updatedCalc.deal_id && c.is_active) return { ...c, is_active: false };
          return c;
        })
      );
    } catch (err) {
      setError(err.message);
    }
  }

  function getItemForm(calcId) {
    return itemForms[calcId] || emptyItemForm;
  }'''
patches.append((old1, new1))

# 2) Tlacitko vedle ceny - jen kdyz NENI aktivni
old2 = '''                  <strong className="mono" style={{ fontSize: 14 }}>{money(c.price_with_vat)}</strong>
                </div>
'''
new2 = '''                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    {!c.is_active && (
                      <button
                        className="btn btn-secondary"
                        style={{ padding: "3px 8px", fontSize: 11.5 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleActivateCalc(c.id);
                        }}
                      >
                        Nastavit jako aktivní
                      </button>
                    )}
                    <strong className="mono" style={{ fontSize: 14 }}>{money(c.price_with_vat)}</strong>
                  </div>
                </div>
'''
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
