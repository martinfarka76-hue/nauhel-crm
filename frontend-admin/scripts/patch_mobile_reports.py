path = "app/reports/page.js"
with open(path) as f:
    content = f.read()

old = '''      <div style={{ display: "flex", gap: 12, margin: "20px 0" }}>
        <KpiCard label="Vážený objem v pipeline" value={formatKc(pipelineWeighted) || "0 Kč"} color="var(--ember-600)" />'''
new = '''      <div className="kpi-row" style={{ display: "flex", gap: 12, margin: "20px 0" }}>
        <KpiCard label="Vážený objem v pipeline" value={formatKc(pipelineWeighted) || "0 Kč"} color="var(--ember-600)" />'''

count = content.count(old)
if count != 1:
    print(f"CHYBA: nalezeno {count}x (ocekavano 1x)")
else:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Patch zapsan uspesne")
