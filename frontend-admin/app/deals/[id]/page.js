"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";
import { STATUS_COLORS, NEXT_MANUAL_STATUS } from "@/lib/constants";

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("cs-CZ");
}

export default function DealDetailPage() {
  const { id } = useParams();
  const [deal, setDeal] = useState(null);
  const [company, setCompany] = useState(null);
  const [calculations, setCalculations] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [error, setError] = useState("");
  const [transitioning, setTransitioning] = useState(false);

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
          <div style={{ fontWeight: 600, marginBottom: 10 }}>Kalkulace</div>
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
            documents.map((d) => (
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
                <div style={{ color: "var(--ink-600)" }}>Vytvořeno: {formatDate(d.created_at)}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </ProtectedShell>
  );
}
