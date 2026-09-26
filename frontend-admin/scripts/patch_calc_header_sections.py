path = "app/deals/[id]/page.js"
with open(path) as f:
    content = f.read()

patches = []

# --- 1) FORMULAR VYTVORENI (create) ---
old_create = '''            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>Produktová řada</label>
                <select
                  value={calcForm.product_line}
                  onChange={(e) => setCalcForm({ ...calcForm, product_line: e.target.value })}
                >
                  <option value="">— vyber —</option>
                  {PRODUCT_LINES.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Dřevina</label>
                <input
                  value={calcForm.wood_species}
                  onChange={(e) => setCalcForm({ ...calcForm, wood_species: e.target.value })}
                  placeholder="např. Modřín"
                />
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>Plocha (m²)</label>
                <input
                  type="number"
                  step="0.01"
                  value={calcForm.area_m2}
                  onChange={(e) => setCalcForm({ ...calcForm, area_m2: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Vzdálenost (km)</label>
                <input
                  type="number"
                  step="0.1"
                  value={calcForm.distance_km}
                  onChange={(e) => setCalcForm({ ...calcForm, distance_km: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Sazba DPH</label>
                <select value={calcForm.vat_rate} onChange={(e) => setCalcForm({ ...calcForm, vat_rate: e.target.value })}>
                  <option value="0.21">21 %</option>
                  <option value="0.12">12 %</option>
                  <option value="0">0 %</option>
                </select>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>Sleva na materiál (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={calcForm.discount_material_percent}
                  onChange={(e) => setCalcForm({ ...calcForm, discount_material_percent: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Sleva na montáž (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={calcForm.discount_installation_percent}
                  onChange={(e) => setCalcForm({ ...calcForm, discount_installation_percent: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Výše zálohy (%)</label>
                <input
                  type="number"
                  step="1"
                  value={calcForm.deposit_percent}
                  onChange={(e) => setCalcForm({ ...calcForm, deposit_percent: e.target.value })}
                />
              </div>
            </div>
            <div className="field">
              <label>Platnost nabídky do</label>
              <input
                type="date"
                value={calcForm.valid_until}
                onChange={(e) => setCalcForm({ ...calcForm, valid_until: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Termín realizace</label>
              <input
                value={calcForm.delivery_terms}
                onChange={(e) => setCalcForm({ ...calcForm, delivery_terms: e.target.value })}
                placeholder="např. 6-8 týdnů od objednávky"
              />
            </div>
            <div className="field">
              <label>Platební podmínky</label>
              <input
                value={calcForm.payment_terms}
                onChange={(e) => setCalcForm({ ...calcForm, payment_terms: e.target.value })}
                placeholder="např. Záloha 50 % při objednávce, doplatek při předání díla"
              />
            </div>
            <div className="field">
              <label>Komentář k nabídce (jen v e-mailu zákazníkovi)</label>
              <textarea
                rows={3}
                value={calcForm.customer_note}
                onChange={(e) => setCalcForm({ ...calcForm, customer_note: e.target.value })}
                placeholder="např. Spojovací vruty jsem zvolil černé nerezové, pro tento druh dřeva ideální a nešpiní."
              />
              <div style={{ fontSize: 11, color: "var(--ink-500)", marginTop: 4 }}>
                Nezobrazuje se na veřejné stránce s nabídkou - jen v e-mailu, kterým se odkaz posílá.
              </div>
            </div>'''

new_create = '''            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--ink-500)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>
              Produkt
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>Produktová řada</label>
                <select
                  value={calcForm.product_line}
                  onChange={(e) => setCalcForm({ ...calcForm, product_line: e.target.value })}
                >
                  <option value="">— vyber —</option>
                  {PRODUCT_LINES.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Dřevina</label>
                <input
                  value={calcForm.wood_species}
                  onChange={(e) => setCalcForm({ ...calcForm, wood_species: e.target.value })}
                  placeholder="např. Modřín"
                />
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 18 }}>
              <div className="field">
                <label>Plocha (m²)</label>
                <input
                  type="number"
                  step="0.01"
                  value={calcForm.area_m2}
                  onChange={(e) => setCalcForm({ ...calcForm, area_m2: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Vzdálenost (km)</label>
                <input
                  type="number"
                  step="0.1"
                  value={calcForm.distance_km}
                  onChange={(e) => setCalcForm({ ...calcForm, distance_km: e.target.value })}
                />
              </div>
            </div>

            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--ink-500)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>
              Obchodní podmínky
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>Sazba DPH</label>
                <select value={calcForm.vat_rate} onChange={(e) => setCalcForm({ ...calcForm, vat_rate: e.target.value })}>
                  <option value="0.21">21 %</option>
                  <option value="0.12">12 %</option>
                  <option value="0">0 %</option>
                </select>
              </div>
              <div className="field">
                <label>Sleva na materiál (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={calcForm.discount_material_percent}
                  onChange={(e) => setCalcForm({ ...calcForm, discount_material_percent: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Sleva na montáž (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={calcForm.discount_installation_percent}
                  onChange={(e) => setCalcForm({ ...calcForm, discount_installation_percent: e.target.value })}
                />
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>Výše zálohy (%)</label>
                <input
                  type="number"
                  step="1"
                  value={calcForm.deposit_percent}
                  onChange={(e) => setCalcForm({ ...calcForm, deposit_percent: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Platnost nabídky do</label>
                <input
                  type="date"
                  value={calcForm.valid_until}
                  onChange={(e) => setCalcForm({ ...calcForm, valid_until: e.target.value })}
                />
              </div>
            </div>
            <div className="field">
              <label>Termín realizace</label>
              <input
                value={calcForm.delivery_terms}
                onChange={(e) => setCalcForm({ ...calcForm, delivery_terms: e.target.value })}
                placeholder="např. 6-8 týdnů od objednávky"
              />
            </div>
            <div className="field" style={{ marginBottom: 18 }}>
              <label>Platební podmínky</label>
              <input
                value={calcForm.payment_terms}
                onChange={(e) => setCalcForm({ ...calcForm, payment_terms: e.target.value })}
                placeholder="např. Záloha 50 % při objednávce, doplatek při předání díla"
              />
            </div>

            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--ink-500)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>
              Poznámka pro zákazníka
            </div>
            <div className="field">
              <label>Komentář k nabídce (jen v e-mailu zákazníkovi)</label>
              <textarea
                rows={3}
                value={calcForm.customer_note}
                onChange={(e) => setCalcForm({ ...calcForm, customer_note: e.target.value })}
                placeholder="např. Spojovací vruty jsem zvolil černé nerezové, pro tento druh dřeva ideální a nešpiní."
              />
              <div style={{ fontSize: 11, color: "var(--ink-500)", marginTop: 4 }}>
                Nezobrazuje se na veřejné stránce s nabídkou - jen v e-mailu, kterým se odkaz posílá.
              </div>
            </div>'''

patches.append(("create form", old_create, new_create))

# --- 2) FORMULAR EDITACE (edit) ---
old_edit = '''                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                          <div className="field">
                            <label>Produktová řada</label>
                            <select
                              value={editCalcForm.product_line}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, product_line: e.target.value })}
                            >
                              <option value="">— vyber —</option>
                              {PRODUCT_LINES.map((p) => (
                                <option key={p} value={p}>
                                  {p}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="field">
                            <label>Dřevina</label>
                            <input
                              value={editCalcForm.wood_species}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, wood_species: e.target.value })}
                            />
                          </div>
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                          <div className="field">
                            <label>Plocha (m²)</label>
                            <input
                              type="number"
                              step="0.01"
                              value={editCalcForm.area_m2}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, area_m2: e.target.value })}
                            />
                          </div>
                          <div className="field">
                            <label>Vzdálenost (km)</label>
                            <input
                              type="number"
                              step="0.1"
                              value={editCalcForm.distance_km}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, distance_km: e.target.value })}
                            />
                          </div>
                          <div className="field">
                            <label>Sazba DPH</label>
                            <select
                              value={editCalcForm.vat_rate}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, vat_rate: e.target.value })}
                            >
                              <option value="0.21">21 %</option>
                              <option value="0.12">12 %</option>
                              <option value="0">0 %</option>
                            </select>
                          </div>
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                          <div className="field">
                            <label>Sleva na materiál (%)</label>
                            <input
                              type="number"
                              step="0.1"
                              value={editCalcForm.discount_material_percent}
                              onChange={(e) =>
                                setEditCalcForm({ ...editCalcForm, discount_material_percent: e.target.value })
                              }
                            />
                          </div>
                          <div className="field">
                            <label>Sleva na montáž (%)</label>
                            <input
                              type="number"
                              step="0.1"
                              value={editCalcForm.discount_installation_percent}
                              onChange={(e) =>
                                setEditCalcForm({ ...editCalcForm, discount_installation_percent: e.target.value })
                              }
                            />
                          </div>
                          <div className="field">
                            <label>Výše zálohy (%)</label>
                            <input
                              type="number"
                              step="1"
                              value={editCalcForm.deposit_percent}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, deposit_percent: e.target.value })}
                            />
                          </div>
                        </div>
                        <div className="field">
                          <label>Platnost nabídky do</label>
                          <input
                            type="date"
                            value={editCalcForm.valid_until}
                            onChange={(e) => setEditCalcForm({ ...editCalcForm, valid_until: e.target.value })}
                          />
                        </div>
                        <div className="field">
                          <label>Termín realizace</label>
                          <input
                            value={editCalcForm.delivery_terms}
                            onChange={(e) => setEditCalcForm({ ...editCalcForm, delivery_terms: e.target.value })}
                          />
                        </div>
                        <div className="field">
                          <label>Platební podmínky</label>
                          <input
                            value={editCalcForm.payment_terms}
                            onChange={(e) => setEditCalcForm({ ...editCalcForm, payment_terms: e.target.value })}
                          />
                        </div>
                        <div className="field">
                          <label>Komentář k nabídce (jen v e-mailu zákazníkovi)</label>
                          <textarea
                            rows={3}
                            value={editCalcForm.customer_note}
                            onChange={(e) => setEditCalcForm({ ...editCalcForm, customer_note: e.target.value })}
                            placeholder="např. Spojovací vruty jsem zvolil černé nerezové, pro tento druh dřeva ideální a nešpiní."
                          />
                          <div style={{ fontSize: 11, color: "var(--ink-500)", marginTop: 4 }}>
                            Nezobrazuje se na veřejné stránce s nabídkou - jen v e-mailu, kterým se odkaz posílá.
                          </div>
                        </div>'''

new_edit = '''                        <div style={{ fontSize: 11, fontWeight: 700, color: "var(--ink-500)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>
                          Produkt
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                          <div className="field">
                            <label>Produktová řada</label>
                            <select
                              value={editCalcForm.product_line}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, product_line: e.target.value })}
                            >
                              <option value="">— vyber —</option>
                              {PRODUCT_LINES.map((p) => (
                                <option key={p} value={p}>
                                  {p}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="field">
                            <label>Dřevina</label>
                            <input
                              value={editCalcForm.wood_species}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, wood_species: e.target.value })}
                            />
                          </div>
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 18 }}>
                          <div className="field">
                            <label>Plocha (m²)</label>
                            <input
                              type="number"
                              step="0.01"
                              value={editCalcForm.area_m2}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, area_m2: e.target.value })}
                            />
                          </div>
                          <div className="field">
                            <label>Vzdálenost (km)</label>
                            <input
                              type="number"
                              step="0.1"
                              value={editCalcForm.distance_km}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, distance_km: e.target.value })}
                            />
                          </div>
                        </div>

                        <div style={{ fontSize: 11, fontWeight: 700, color: "var(--ink-500)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>
                          Obchodní podmínky
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                          <div className="field">
                            <label>Sazba DPH</label>
                            <select
                              value={editCalcForm.vat_rate}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, vat_rate: e.target.value })}
                            >
                              <option value="0.21">21 %</option>
                              <option value="0.12">12 %</option>
                              <option value="0">0 %</option>
                            </select>
                          </div>
                          <div className="field">
                            <label>Sleva na materiál (%)</label>
                            <input
                              type="number"
                              step="0.1"
                              value={editCalcForm.discount_material_percent}
                              onChange={(e) =>
                                setEditCalcForm({ ...editCalcForm, discount_material_percent: e.target.value })
                              }
                            />
                          </div>
                          <div className="field">
                            <label>Sleva na montáž (%)</label>
                            <input
                              type="number"
                              step="0.1"
                              value={editCalcForm.discount_installation_percent}
                              onChange={(e) =>
                                setEditCalcForm({ ...editCalcForm, discount_installation_percent: e.target.value })
                              }
                            />
                          </div>
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                          <div className="field">
                            <label>Výše zálohy (%)</label>
                            <input
                              type="number"
                              step="1"
                              value={editCalcForm.deposit_percent}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, deposit_percent: e.target.value })}
                            />
                          </div>
                          <div className="field">
                            <label>Platnost nabídky do</label>
                            <input
                              type="date"
                              value={editCalcForm.valid_until}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, valid_until: e.target.value })}
                            />
                          </div>
                        </div>
                        <div className="field">
                          <label>Termín realizace</label>
                          <input
                            value={editCalcForm.delivery_terms}
                            onChange={(e) => setEditCalcForm({ ...editCalcForm, delivery_terms: e.target.value })}
                          />
                        </div>
                        <div className="field" style={{ marginBottom: 18 }}>
                          <label>Platební podmínky</label>
                          <input
                            value={editCalcForm.payment_terms}
                            onChange={(e) => setEditCalcForm({ ...editCalcForm, payment_terms: e.target.value })}
                          />
                        </div>

                        <div style={{ fontSize: 11, fontWeight: 700, color: "var(--ink-500)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>
                          Poznámka pro zákazníka
                        </div>
                        <div className="field">
                          <label>Komentář k nabídce (jen v e-mailu zákazníkovi)</label>
                          <textarea
                            rows={3}
                            value={editCalcForm.customer_note}
                            onChange={(e) => setEditCalcForm({ ...editCalcForm, customer_note: e.target.value })}
                            placeholder="např. Spojovací vruty jsem zvolil černé nerezové, pro tento druh dřeva ideální a nešpiní."
                          />
                          <div style={{ fontSize: 11, color: "var(--ink-500)", marginTop: 4 }}>
                            Nezobrazuje se na veřejné stránce s nabídkou - jen v e-mailu, kterým se odkaz posílá.
                          </div>
                        </div>'''

patches.append(("edit form", old_edit, new_edit))

ok = True
for name, old, new in patches:
    count = content.count(old)
    if count != 1:
        print(f"CHYBA ({name}): nalezeno {count}x (ocekavano 1x)")
        ok = False
    else:
        content = content.replace(old, new)

if ok:
    with open(path, 'w') as f:
        f.write(content)
    print("Oba formulare (vytvoreni i editace) prepsany uspesne")
else:
    print("NIC nebylo zapsano kvuli chybe vyse")
