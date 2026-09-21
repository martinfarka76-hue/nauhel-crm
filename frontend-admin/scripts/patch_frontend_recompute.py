path = "app/deals/[id]/page.js"
with open(path) as f:
    content = f.read()

patches = []

# 1) emptyItemForm - pridat wood_species_id
old1 = 'const emptyItemForm = { category: "Materiál", name: "", unit: "", quantity: "", unit_price: "", item_area_m2: "" };'
new1 = 'const emptyItemForm = { category: "Materiál", name: "", unit: "", quantity: "", unit_price: "", item_area_m2: "", wood_species_id: "" };'
patches.append((old1, new1))

# 2) Prepsat handleApplyWoodSpecies - vytahnout vypocet ceny do samostatne
#    funkce computeUnitPriceForSpecies (znovupouzitelne pro prepocet),
#    a ulozit wood_species_id do polozky.
old2 = '''  function handleApplyWoodSpecies(calcId, speciesId, productLine, areaM2) {
    const species = woodSpeciesList.find((s) => s.id === speciesId);
    if (!species) return;

    // Krycí plocha (co chce zákazník) vs. skutečné množství materiálu (co musíme
    // nakoupit) - u profilů s perem/drážkou je efektivní krycí šířka menší než
    // šířka prkna, takže je potřeba víc materiálu, než kolik reálně pokryje fasádu.
    const widthMm = Number(species.width_mm) || 0;
    const widthEffMm = Number(species.width_effective_mm) || 0;
    const facadeArea = areaM2 ? Number(areaM2) : Number(getItemForm(calcId).quantity) || 0;

    let materialQuantity = facadeArea;
    let itemName = species.name;
    if (widthMm > 0 && widthEffMm > 0 && widthEffMm < widthMm && facadeArea > 0) {
      materialQuantity = Math.round(facadeArea * (widthMm / widthEffMm) * 100) / 100;
      itemName = `${species.name} (Krycí plocha fasády: ${facadeArea} m² → potřebné množství materiálu: ${materialQuantity} m²)`;
    }

    // Cena za m² - přesně podle listu "Kalkulace" ve zdrojovém Excelu: materiál
    // a výroba se počítají ODDĚLENĚ, každé se svou marží, a marže výroby se liší
    // podle produktové řady (Atacama = plná marže, Mirage/Ocaso = poloviční).
    // K materiálu se navíc připočítává fixní náklad "doprava - nákup dřeva"
    // (jednou za zakázku, ne za m²), teprve pak se na součet aplikuje marže.
    const marginMaterial = pricingParams.margin_material ?? 0;
    const marginVyroba = pricingParams.margin_vyroba ?? 0;
    const productionMarginEffective = productLine === "Atacama" ? marginVyroba : marginVyroba * 0.5;

    const surchargeKey = surchargeKeyForProductLine(productLine);
    const surcharge = surchargeKey ? pricingParams[surchargeKey] ?? 0 : 0;
    const productionBase = pricingParams.production_base_per_m2 ?? 0;
    const packagingBase = pricingParams.packaging_base_per_m2 ?? 0;
    const transportFixedFromSupplier = pricingParams.transport_fixed_from_supplier ?? 0;
    const purchasePrice = Number(species.purchase_price_per_m2) || 0;

    const vyrobaZaklad = materialQuantity * (productionBase + surcharge);
    const baleniCelkem = materialQuantity * packagingBase;
    const vyrobaSMarzi = (vyrobaZaklad + baleniCelkem) * (1 + productionMarginEffective);

    const materialZaklad = materialQuantity * purchasePrice + transportFixedFromSupplier;
    const materialSMarzi = materialZaklad * (1 + marginMaterial);

    const cenaCelkem = materialSMarzi + vyrobaSMarzi;
    const suggestedPrice = materialQuantity > 0 ? Math.round((cenaCelkem / materialQuantity) * 100) / 100 : 0;

    setItemForm(calcId, {
      category: "Materiál",
      name: itemName,
      unit: "m²",
      quantity: areaM2 ? String(materialQuantity) : getItemForm(calcId).quantity,
      unit_price: String(suggestedPrice),
    });
  }'''
new2 = '''  // Cena za m² - přesně podle listu "Kalkulace" ve zdrojovém Excelu: materiál
  // a výroba se počítají ODDĚLENĚ, každé se svou marží, a marže výroby se liší
  // podle produktové řady (Atacama = plná marže, Mirage/Ocaso = poloviční).
  // K materiálu se navíc připočítává fixní náklad "doprava - nákup dřeva"
  // (jednou za zakázku, ne za m²), teprve pak se na součet aplikuje marže.
  // Sdílené jak pro předvyplnění nové položky, tak pro pozdější přepočet
  // podle jiné produktové řady/dřeviny.
  function computeUnitPriceForSpecies(species, productLine, materialQuantity) {
    const marginMaterial = pricingParams.margin_material ?? 0;
    const marginVyroba = pricingParams.margin_vyroba ?? 0;
    const productionMarginEffective = productLine === "Atacama" ? marginVyroba : marginVyroba * 0.5;

    const surchargeKey = surchargeKeyForProductLine(productLine);
    const surcharge = surchargeKey ? pricingParams[surchargeKey] ?? 0 : 0;
    const productionBase = pricingParams.production_base_per_m2 ?? 0;
    const packagingBase = pricingParams.packaging_base_per_m2 ?? 0;
    const transportFixedFromSupplier = pricingParams.transport_fixed_from_supplier ?? 0;
    const purchasePrice = Number(species.purchase_price_per_m2) || 0;

    const vyrobaZaklad = materialQuantity * (productionBase + surcharge);
    const baleniCelkem = materialQuantity * packagingBase;
    const vyrobaSMarzi = (vyrobaZaklad + baleniCelkem) * (1 + productionMarginEffective);

    const materialZaklad = materialQuantity * purchasePrice + transportFixedFromSupplier;
    const materialSMarzi = materialZaklad * (1 + marginMaterial);

    const cenaCelkem = materialSMarzi + vyrobaSMarzi;
    return materialQuantity > 0 ? Math.round((cenaCelkem / materialQuantity) * 100) / 100 : 0;
  }

  function handleApplyWoodSpecies(calcId, speciesId, productLine, areaM2) {
    const species = woodSpeciesList.find((s) => s.id === speciesId);
    if (!species) return;

    // Krycí plocha (co chce zákazník) vs. skutečné množství materiálu (co musíme
    // nakoupit) - u profilů s perem/drážkou je efektivní krycí šířka menší než
    // šířka prkna, takže je potřeba víc materiálu, než kolik reálně pokryje fasádu.
    const widthMm = Number(species.width_mm) || 0;
    const widthEffMm = Number(species.width_effective_mm) || 0;
    const facadeArea = areaM2 ? Number(areaM2) : Number(getItemForm(calcId).quantity) || 0;

    let materialQuantity = facadeArea;
    let itemName = species.name;
    if (widthMm > 0 && widthEffMm > 0 && widthEffMm < widthMm && facadeArea > 0) {
      materialQuantity = Math.round(facadeArea * (widthMm / widthEffMm) * 100) / 100;
      itemName = `${species.name} (Krycí plocha fasády: ${facadeArea} m² → potřebné množství materiálu: ${materialQuantity} m²)`;
    }

    const suggestedPrice = computeUnitPriceForSpecies(species, productLine, materialQuantity);

    setItemForm(calcId, {
      category: "Materiál",
      name: itemName,
      unit: "m²",
      quantity: areaM2 ? String(materialQuantity) : getItemForm(calcId).quantity,
      unit_price: String(suggestedPrice),
      wood_species_id: speciesId,
    });
  }

  async function handleRecomputeItems(calcId) {
    const calc = calculations.find((c) => c.id === calcId);
    const items = calcItems[calcId] || [];
    const toUpdate = items.filter((item) => item.wood_species_id);
    if (toUpdate.length === 0) {
      alert(
        "Žádná položka v této kalkulaci nemá uloženou dřevinu k přepočtu (byla přidána ručně, nebo z ceníku partnera)."
      );
      return;
    }
    if (
      !window.confirm(
        `Přepočítat cenu u ${toUpdate.length} položek podle aktuální produktové řady ` +
          `("${calc.product_line || "—"}")? Množství zůstane stejné, přepočítá se jen cena za jednotku.`
      )
    )
      return;

    setError("");
    try {
      let lastUpdatedCalc = null;
      for (const item of toUpdate) {
        const species = woodSpeciesList.find((s) => s.id === item.wood_species_id);
        if (!species) continue;
        const newPrice = computeUnitPriceForSpecies(species, calc.product_line, Number(item.quantity));
        lastUpdatedCalc = await api.put(`/calculation-items/${item.id}`, { unit_price: newPrice });
      }
      if (lastUpdatedCalc) {
        setCalculations((prev) => prev.map((c) => (c.id === calcId ? lastUpdatedCalc : c)));
      }
      const newItems = await api.get(`/calculations/${calcId}/items`);
      setCalcItems((prev) => ({ ...prev, [calcId]: newItems }));
    } catch (err) {
      setError(err.message);
    }
  }'''
patches.append((old2, new2))

# 3) handleAddItem - poslat wood_species_id v payloadu
old3 = '''      const updatedCalc = await api.post(`/calculations/${calcId}/items`, {
        category: form.category,
        name: form.name,
        unit: form.unit || null,
        quantity: Number(form.quantity),
        unit_price: Number(form.unit_price),
        display_order: (calcItems[calcId] || []).length,
      });'''
new3 = '''      const updatedCalc = await api.post(`/calculations/${calcId}/items`, {
        category: form.category,
        name: form.name,
        unit: form.unit || null,
        quantity: Number(form.quantity),
        unit_price: Number(form.unit_price),
        display_order: (calcItems[calcId] || []).length,
        wood_species_id: form.wood_species_id || null,
      });'''
patches.append((old3, new3))

# 4) Tlacitko v UI vedle "Polozky kalkulace"
old4 = '''                      <div style={{ fontSize: 12, fontWeight: 700, color: "var(--ink-600)", marginBottom: 6 }}>
                        Položky kalkulace
                      </div>'''
new4 = '''                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--ink-600)" }}>
                          Položky kalkulace
                        </div>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ padding: "3px 8px", fontSize: 11.5 }}
                          onClick={() => handleRecomputeItems(c.id)}
                          title="Přepočítá cenu u položek vytvořených přes 'Předvyplnit z dřeviny' podle aktuální produktové řady v hlavičce - množství zůstane stejné."
                        >
                          🔄 Přepočítat podle produktové řady
                        </button>
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
