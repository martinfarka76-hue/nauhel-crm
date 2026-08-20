"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";
import { STATUS_COLORS } from "@/lib/constants";

export default function CompanyDetailPage() {
  const { id } = useParams();
  const [company, setCompany] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [deals, setDeals] = useState([]);
  const [error, setError] = useState("");
  const [showDealForm, setShowDealForm] = useState(false);
  const [dealForm, setDealForm] = useState({ name: "", price: "" });
  const [saving, setSaving] = useState(false);

  function loadAll() {
    Promise.all([
      api.get(`/companies/${id}`),
      api.get(`/contacts?company_id=${id}`),
      api.get(`/deals?company_id=${id}`),
    ])
      .then(([c, ct, d]) => {
        setCompany(c);
        setContacts(ct);
        setDeals(d);
      })
      .catch((err) => setError(err.message));
  }

  useEffect(loadAll, [id]);

  async function handleCreateDeal(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.post("/deals", {
        company_id: id,
        name: dealForm.name,
        status: "Lead",
        price: dealForm.price ? Number(dealForm.price) : null,
      });
      setDealForm({ name: "", price: "" });
      setShowDealForm(false);
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (!company) {
    return (
      <ProtectedShell>
        {error ? <div className="error-banner">{error}</div> : <div className="empty-state">Načítám…</div>}
      </ProtectedShell>
    );
  }

  return (
    <ProtectedShell>
      <h1 className="page-title">{company.name}</h1>
      <p className="page-subtitle">
        {company.ico ? `IČO ${company.ico}` : ""} {company.dic ? `· DIČ ${company.dic}` : ""}
      </p>

      {error && <div className="error-banner">{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 28 }}>
        <div className="card">
          <div style={{ fontWeight: 600, marginBottom: 10 }}>Údaje o firmě</div>
          <div style={{ fontSize: 13.5, color: "var(--ink-600)", lineHeight: 1.8 }}>
            <div>Adresa: {company.address || "—"}</div>
            <div>Poznámky: {company.notes || "—"}</div>
          </div>
        </div>
        <div className="card">
          <div style={{ fontWeight: 600, marginBottom: 10 }}>Kontaktní osoby</div>
          {contacts.length === 0 ? (
            <div style={{ fontSize: 13.5, color: "var(--ink-400)" }}>Zatím žádné kontakty</div>
          ) : (
            contacts.map((c) => (
              <div key={c.id} style={{ fontSize: 13.5, marginBottom: 6 }}>
                <strong>{c.first_name} {c.last_name}</strong>
                {c.position ? ` — ${c.position}` : ""}
                <div style={{ color: "var(--ink-600)" }}>{c.email} {c.phone}</div>
              </div>
            ))
          )}
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={{ fontWeight: 600 }}>Obchodní případy</div>
        <button className="btn btn-secondary" onClick={() => setShowDealForm(!showDealForm)}>
          {showDealForm ? "Zrušit" : "+ Nový případ"}
        </button>
      </div>

      {showDealForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <form onSubmit={handleCreateDeal}>
            <div className="field">
              <label>Název případu *</label>
              <input
                required
                value={dealForm.name}
                onChange={(e) => setDealForm({ ...dealForm, name: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Odhadovaná cena (Kč)</label>
              <input
                type="number"
                value={dealForm.price}
                onChange={(e) => setDealForm({ ...dealForm, price: e.target.value })}
              />
            </div>
            <button className="btn btn-primary" type="submit" disabled={saving}>
              {saving ? "Ukládám…" : "Vytvořit případ"}
            </button>
          </form>
        </div>
      )}

      {deals.length === 0 ? (
        <div className="empty-state">Zatím žádné obchodní případy.</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Název</th>
              <th>Stav</th>
              <th>Cena</th>
            </tr>
          </thead>
          <tbody>
            {deals.map((d) => (
              <tr key={d.id} className="clickable" onClick={() => (window.location.href = `/deals/${d.id}`)}>
                <td style={{ fontWeight: 600 }}>{d.name}</td>
                <td>
                  <span className="badge" style={{ background: STATUS_COLORS[d.status] }}>
                    {d.status}
                  </span>
                </td>
                <td className="mono">{d.price ? Number(d.price).toLocaleString("cs-CZ") + " Kč" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </ProtectedShell>
  );
}
