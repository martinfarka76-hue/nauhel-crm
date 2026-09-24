path = "app/deals/[id]/page.js"
with open(path) as f:
    content = f.read()

patches = []

# 1) Nova funkce hned za handleDownloadDeliveryNote
old1 = '''  async function handleSendInvoiceEmail(documentId) {
    if (!window.confirm("Odeslat fakturu zákazníkovi emailem (odkaz + PDF příloha)?")) return;'''
new1 = '''  async function handleDownloadVopSnapshot(documentId) {
    setError("");
    try {
      const res = await fetch(`${API_URL}/documents/${documentId}/vop-snapshot`, {
        headers: { Authorization: `Bearer ${getAuthToken()}` },
      });
      if (!res.ok) throw new Error("Stažení snapshotu VOP selhalo.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "VOP_snapshot.pdf";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSendInvoiceEmail(documentId) {
    if (!window.confirm("Odeslat fakturu zákazníkovi emailem (odkaz + PDF příloha)?")) return;'''
patches.append((old1, new1))

# 2) Zobrazeni IP + odkaz na snapshot VOP hned za "Potvrdil(a)... dne..."
old2 = '''                {d.document_type === "Objednávka" && d.confirmed_at && (
                  <div style={{ fontSize: 11.5, color: "var(--ink-600)", marginTop: 2 }}>
                    Potvrdil(a) {d.confirmed_by_name} dne {formatDate(d.confirmed_at)}
                  </div>
                )}'''
new2 = '''                {d.document_type === "Objednávka" && d.confirmed_at && (
                  <div style={{ fontSize: 11.5, color: "var(--ink-600)", marginTop: 2 }}>
                    Potvrdil(a) {d.confirmed_by_name} dne {formatDate(d.confirmed_at)}
                    {d.confirmation_ip_address && ` · IP ${d.confirmation_ip_address}`}
                    {d.vop_snapshot_filename && (
                      <>
                        {" · "}
                        <button
                          onClick={() => handleDownloadVopSnapshot(d.id)}
                          style={{
                            background: "none",
                            border: "none",
                            padding: 0,
                            color: "var(--ember-500)",
                            textDecoration: "underline",
                            cursor: "pointer",
                            fontSize: 11.5,
                          }}
                          title={`Otisk (SHA-256): ${d.vop_snapshot_sha256 || "—"}`}
                        >
                          znění VOP v době potvrzení
                        </button>
                      </>
                    )}
                  </div>
                )}'''
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
