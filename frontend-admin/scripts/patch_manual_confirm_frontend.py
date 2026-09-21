path = "app/deals/[id]/page.js"
with open(path) as f:
    content = f.read()

patches = []

# 1) Novy handler hned za handleManualOrderConfirmation
old1 = '''  async function handleManualOrderConfirmation() {
    const note = window.prompt(
      "Jak/kde byla objednávka potvrzena mimo systém? (např. \\"potvrzeno telefonicky, viz HubSpot\\")"
    );
    if (!note || !note.trim()) return;

    setTransitioning(true);
    setError("");
    try {
      await api.post(`/deals/${id}/manual-order-confirmation`, { note: note.trim() });
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setTransitioning(false);
    }
  }'''
new1 = old1 + '''

  async function handleManualConfirmOrder() {
    if (!latestObjednavka) return;
    const confirmedByName = window.prompt(
      "Kdo objednávku potvrdil? (celé jméno zákazníka, pro záznam)"
    );
    if (!confirmedByName || !confirmedByName.trim()) return;

    setTransitioning(true);
    setError("");
    try {
      await api.post(`/documents/${latestObjednavka.id}/manual-confirm`, {
        confirmed_by_name: confirmedByName.trim(),
        agreed_to_terms: true,
      });
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setTransitioning(false);
    }
  }'''
patches.append((old1, new1))

# 2) Popisek + tlacitko v "Co dal" pro cekajici potvrzeni
old2 = '''          description: deal.skip_customer_emails
            ? "E-mail se u tohoto případu neposílá (ruční vyplňování do formuláře zákazníka) - jakmile " +
              "zákazník objednávku potvrdí (mimo systém), přesuň případ ručně dál."
            : "Zákazník dostal e-mail s odkazem na potvrzení objednávky. Jakmile ji potvrdí, automaticky " +
              "vznikne zálohová faktura a případ se posune dál.",
        };
      }'''
new2 = '''          description: deal.skip_customer_emails
            ? "E-mail se u tohoto případu neposílá (ruční vyplňování do formuláře zákazníka) - jakmile " +
              "zákazník objednávku potvrdí (mimo systém), potvrď to tlačítkem níže."
            : "Zákazník dostal e-mail s odkazem na potvrzení objednávky. Jakmile ji potvrdí, automaticky " +
              "vznikne zálohová faktura a případ se posune dál.",
          actionLabel: deal.skip_customer_emails ? "Ručně potvrdit objednávku" : undefined,
          action: deal.skip_customer_emails ? handleManualConfirmOrder : undefined,
        };
      }'''
patches.append((old2, new2))

# 3) Presun odznaku "Rucni formular" pryc od hlavniho stavoveho odznaku,
#    k odkazu na SharePoint slozku, jako tlumenejsi poznamku
old3 = '''        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {deal.skip_customer_emails && (
            <span
              className="badge"
              title="E-maily s nabídkou/objednávkou se u tohoto případu neposílají automaticky - vyplňuje se ručně do formuláře zákazníka."
              style={{
                background: "#fdf3ec",
                border: "1px solid var(--ember-500)",
                color: "var(--ember-600)",
                fontSize: 12,
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              🚫✉️ Ruční formulář
            </span>
          )}
          <span'''
new3 = '''        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span'''
patches.append((old3, new3))

old4 = '''              <span>
                <a href={deal.sharepoint_folder_url} target="_blank" rel="noopener noreferrer">
                  📁 Otevřít složku na SharePointu
                </a>
              </span>
            )}
          </div>'''
new4 = '''              <span>
                <a href={deal.sharepoint_folder_url} target="_blank" rel="noopener noreferrer">
                  📁 Otevřít složku na SharePointu
                </a>
              </span>
            )}
            {deal.skip_customer_emails && (
              <span
                title="E-maily s nabídkou/objednávkou se u tohoto případu neposílají automaticky - vyplňuje se ručně do formuláře zákazníka."
                style={{ fontSize: 12, color: "var(--ink-400)" }}
              >
                🚫✉️ ruční formulář
              </span>
            )}
          </div>'''
patches.append((old4, new4))

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
    print("Vsechny 4 patche zapsany uspesne")
else:
    print("NIC nebylo zapsano kvuli chybe vyse")
