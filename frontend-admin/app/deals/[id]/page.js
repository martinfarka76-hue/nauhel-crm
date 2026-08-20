"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";
import { STATUS_COLORS, NEXT_MANUAL_STATUS } from "@/lib/constants";

const PUBLIC_URL = process.env.NEXT_PUBLIC_PUBLIC_URL || "http://localhost:18082";

function formatDate(iso) {
  if (!iso) return "—";
  // Backend posílá "naive" datetime v UTC (bez timezone značky) - doplníme
  // "Z", ať to prohlížeč správně převede na místní čas, ne zobrazí čas
  // tak jak je (což by bylo o 1-2 hodiny méně, podle letního/zimního času).
  const utcIso = iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z";
  return new Date(utcIso).toLocaleString("cs-CZ");
}

export default function DealDetailPage() {
  const { id } = useParams();
  const [deal, setDeal] = useState(null);
  const [company, setCompany] = useState(null);
  const [calculations, setCalculations] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [documentViews, setDocumentViews] = useState({}); // { [documentId]: [views] }
  const [expandedDoc, setExpandedDoc] = useState(null);
  const [copiedDoc, setCopiedDoc] = useState(null);
  const [error, setError] = useState("");
  const [transitioning, setTransitioning] = useState(false);
  const [showCalcForm, setShowCalcForm] = useState(false);
  const [calcSaving, setCalcSaving] = useState(false);
  const [calcForm, setCalcForm] = useState({
    product_line: "",
    wood_species: "",
    area_m2: "",
    distance_km: "",
    vat_rate: "0.21",
    price_without_vat: "",
    unit_price_per_m2: "",
    valid_until: "",
  });

  function loadAll() {
    api
      .get(`/deals/${id}`)
      .then((d) => {
        setDeal(d);
        return Promise.all([
          api.get(`/companies/${d.company_id}`),
          api.get(`/deals/${id}/calculations`),
          api.get(`/deals/${id}/documents`),
        ]);
      })
      .then(([c, calcs, docs]) => {
        setCompany(c);
        setCalculations(calcs);
        setDocuments(docs);
      })
      .catch((err) => setError(err.message));
  }

  useEffect(loadAll, [id]);

  function handleCopyLink(accessToken, docId) {
    const url = `${PUBLIC_URL}/n/${accessToken}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopiedDoc(docId);
      setTimeout(() => setCopiedDoc(null), 2000);
    });
  }

  async function handleToggleViews(docId) {
    if (expandedDoc === docId) {
      setExpandedDoc(null);
      return;
    }
    setExpandedDoc(docId);
    await refreshViews(docId);
  }

  async function refreshViews(docId) {
    setDocumentViews((prev) => ({ ...prev, [docId]: undefined }));
    try {
      const views = await api.get(`/documents/${docId}/views`);
      setDocumentViews((prev) => ({ ...prev, [docId]: views }));
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleTransition(toStatus) {
    setTransitioning(true);
    setError("");
    try {
      await api.post(`/deals/${id}/transition`, { to_status: toStatus });
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setTransitioning(false);
    }
  }

  async function handleCreateCalculation(e) {
    e.preventDefault();
    setCalcSaving(true);
    setError("");
    try {
      const priceWithoutVat = Number(calcForm.price_without_vat) || 0;
      const vatRate = Number(calcForm.vat_rate) || 0;
      const vatAmount = Math.round(priceWithoutVat * vatRate * 100) / 100;
      const priceWithVat = Math.round((priceWithoutVat + vatAmount) * 100) / 100;

      await api.post(`/deals/${id}/calculations`, {
        product_line: calcForm.product_line || null,
        wood_species: calcForm.wood_species || null,
        area_m2: calcForm.area_m2 ? Number(calcForm.area_m2) : null,
        distance_km: calcForm.distance_km ? Number(calcForm.distance_km) : null,
        vat_rate: vatRate,
        price_without_vat: priceWithoutVat,
        vat_amount: vatAmount,
        price_with_vat: priceWithVat,
        unit_price_per_m2: calcForm.unit_price_per_m2 ? Number(calcForm.unit_price_per_m2) : null,
        valid_until: calcForm.valid_until || null,
      });
      setCalcForm({
        product_line: "",
        wood_species: "",
        area_m2: "",
        distance_km: "",
        vat_rate: "0.21",
        price_without_vat: "",
        unit_price_per_m2: "",
        valid_until: "",
      });
      setShowCalcForm(false);
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setCalcSaving(false);
    }
  }

  if (!deal) {
    return (
      <ProtectedShell>
        {error ? <div className="error-banner">{error}</div> : <div className="empty-state">Načítám…</div>}
      </ProtectedShell>
    );
  }

  const nextStatus = NEXT_MANUAL_STATUS[deal.status];
  const activeCalc = calculations.find((c) => c.is_active);

  return (
    <ProtectedShell>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 className="page-title">{deal.name}</h1>
          <p className="page-subtitle">
            {company ? (
              <a href={`/companies/${company.id}`} style={{ textDecoration: "underline" }}>
                {company.name}
              </a>
            ) : (
              "—"
            )}
          </p>
        </div>
        <span className="badge" style={{ background: STATUS_COLORS[deal.status], fontSize: 13 }}>
          {deal.status}
        </span>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ fontWeight: 600, marginBottom: 12 }}>Přechod stavu</div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {nextStatus && (
            <button
              className="btn btn-primary"
              disabled={transitioning}
              onClick={() => handleTransition(nextStatus)}
            >
              Přesunout do: {nextStatus}
            </button>
          )}
          {deal.status === "Objednávka" && (
            <div style={{ fontSize: 13, color: "var(--ink-600)", alignSelf: "center" }}>
              Další krok (Zálohová faktura) proběhne automaticky po potvrzení e-signature.
            </div>
          )}
          {deal.status !== "Ztraceno" && deal.status !== "Fakturováno" && (
            <button
              className="btn btn-danger"
              disabled={transitioning}
              onClick={() => handleTransition("Ztraceno")}
            >
              Označit jako ztracené
            </button>
          )}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <div style={{ fontWeight: 600 }}>Kalkulace</div>
            <button className="btn btn-secondary" onClick={() => setShowCalcForm(!showCalcForm)}>
              {showCalcForm ? "Zrušit" : "+ Nová kalkulace"}
            </button>
          </div>

          {showCalcForm && (
            <form onSubmit={handleCreateCalculation} style={{ marginBottom: 16, paddingBottom: 16, borderBottom: "1px solid var(--paper-200)" }}>
              <div className="field">
                <label>Produktová řada</label>
                <input
                  value={calcForm.product_line}
                  onChange={(e) => setCalcForm({ ...calcForm, product_line: e.target.value })}
                  placeholder="např. Atacama"
                />
              </div>
              <div className="field">
                <label>Dřevina</label>
                <input
                  value={calcForm.wood_species}
                  onChange={(e) => setCalcForm({ ...calcForm, wood_species: e.target.value })}
                  placeholder="např. Modřín"
                />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
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
              <div className="field">
                <label>Sazba DPH</label>
                <select
                  value={calcForm.vat_rate}
                  onChange={(e) => setCalcForm({ ...calcForm, vat_rate: e.target.value })}
                >
                  <option value="0.21">21 %</option>
                  <option value="0.12">12 %</option>
                  <option value="0">0 %</option>
                </select>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div className="field">
                  <label>Cena bez DPH (Kč) *</label>
                  <input
                    type="number"
                    required
                    value={calcForm.price_without_vat}
                    onChange={(e) => setCalcForm({ ...calcForm, price_without_vat: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Cena za m² (Kč)</label>
                  <input
                    type="number"
                    value={calcForm.unit_price_per_m2}
                    onChange={(e) => setCalcForm({ ...calcForm, unit_price_per_m2: e.target.value })}
                  />
                </div>
              </div>
              {calcForm.price_without_vat && (
                <div style={{ fontSize: 12.5, color: "var(--ink-600)", marginBottom: 12 }}>
                  DPH a cena s DPH se dopočítají automaticky podle zvolené sazby.
                </div>
              )}
              <div className="field">
                <label>Platnost nabídky do</label>
                <input
                  type="date"
                  value={calcForm.valid_until}
                  onChange={(e) => setCalcForm({ ...calcForm, valid_until: e.target.value })}
                />
              </div>
              <button className="btn btn-primary" type="submit" disabled={calcSaving}>
                {calcSaving ? "Ukládám…" : "Uložit kalkulaci"}
              </button>
            </form>
          )}

          {calculations.length === 0 ? (
            <div style={{ fontSize: 13.5, color: "var(--ink-400)" }}>Zatím žádná kalkulace</div>
          ) : (
            calculations.map((c) => (
              <div
                key={c.id}
                style={{
                  fontSize: 13.5,
                  marginBottom: 10,
                  paddingBottom: 10,
                  borderBottom: "1px solid var(--paper-200)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong>{c.product_line || "—"} {c.wood_species ? `/ ${c.wood_species}` : ""}</strong>
                  {c.is_active && (
                    <span className="badge" style={{ background: "var(--success)" }}>aktivní</span>
                  )}
                </div>
                <div className="mono" style={{ color: "var(--ink-600)" }}>
                  {c.price_with_vat ? Number(c.price_with_vat).toLocaleString("cs-CZ") + " Kč s DPH" : "—"}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="card">
          <div style={{ fontWeight: 600, marginBottom: 10 }}>Dokumenty</div>
          {documents.length === 0 ? (
            <div style={{ fontSize: 13.5, color: "var(--ink-400)" }}>Zatím žádné dokumenty</div>
          ) : (
            documents.map((d) => {
              const views = documentViews[d.id];
              const viewCount = views ? views.length : null;
              const lastView = views && views.length > 0 ? views[0] : null;

              return (
                <div
                  key={d.id}
                  style={{
                    fontSize: 13.5,
                    marginBottom: 10,
                    paddingBottom: 10,
                    borderBottom: "1px solid var(--paper-200)",
                  }}
                >
                  <div>
                    <strong>{d.document_type}</strong> {d.version > 1 ? `(v${d.version})` : ""}
                  </div>
                  <div style={{ color: "var(--ink-600)", marginBottom: 6 }}>
                    Vytvořeno: {formatDate(d.created_at)}
                  </div>

                  {d.document_type === "Nabídka" && (
                    <>
                      <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: "5px 10px", fontSize: 12.5 }}
                          onClick={() => handleCopyLink(d.access_token, d.id)}
                        >
                          {copiedDoc === d.id ? "Zkopírováno ✓" : "Zkopírovat veřejný odkaz"}
                        </button>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: "5px 10px", fontSize: 12.5 }}
                          onClick={() => handleToggleViews(d.id)}
                        >
                          {expandedDoc === d.id ? "Skrýt zobrazení" : "Zobrazit sledování"}
                        </button>
                      </div>

                      {expandedDoc === d.id && (
                        <div
                          style={{
                            background: "var(--paper-50)",
                            borderRadius: 6,
                            padding: "10px 12px",
                            marginTop: 4,
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                            <div style={{ fontWeight: 600 }}>
                              {views ? `Otevřeno ${viewCount}×` : "Sledování"}
                            </div>
                            <button
                              className="btn btn-secondary"
                              style={{ padding: "3px 8px", fontSize: 11.5 }}
                              onClick={() => refreshViews(d.id)}
                            >
                              Obnovit
                            </button>
                          </div>
                          {!views ? (
                            <div style={{ color: "var(--ink-400)" }}>Načítám…</div>
                          ) : views.length === 0 ? (
                            <div style={{ color: "var(--ink-400)" }}>
                              Nabídka zatím nebyla otevřena.
                            </div>
                          ) : (
                            views.map((v) => (
                              <div key={v.id} style={{ color: "var(--ink-600)", marginBottom: 3 }}>
                                {formatDate(v.viewed_at)}
                                {v.duration_seconds != null
                                  ? ` · prohlíženo ${v.duration_seconds} s`
                                  : " · doba čtení neznámá"}
                              </div>
                            ))
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </ProtectedShell>
  );
}
