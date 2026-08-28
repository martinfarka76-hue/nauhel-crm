"use client";

import { useEffect, useState } from "react";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";

export default function CompaniesPage() {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", ico: "", dic: "", website: "", address: "" });
  const [saving, setSaving] = useState(false);
  const [aresLoading, setAresLoading] = useState(false);
  const [aresError, setAresError] = useState("");

  function loadCompanies() {
    setLoading(true);
    api
      .get("/companies")
      .then((data) => setCompanies([...data].sort((a, b) => a.name.localeCompare(b.name, "cs"))))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(loadCompanies, []);

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.post("/companies", form);
      setForm({ name: "", ico: "", dic: "", website: "", address: "" });
      setShowForm(false);
      loadCompanies();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleAresLookup() {
    if (!form.ico) {
      setAresError("Nejdřív vyplň IČO.");
      return;
    }
    setAresLoading(true);
    setAresError("");
    try {
      const result = await api.get(`/ares/${form.ico}`);
      setForm({
        ...form,
        name: result.name || form.name,
        address: result.address || form.address,
        dic: result.dic_guess || form.dic,
      });
    } catch (err) {
      setAresError(err.message);
    } finally {
      setAresLoading(false);
    }
  }

  return (
    <ProtectedShell>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 className="page-title">Firmy</h1>
          <p className="page-subtitle">Zákazníci a jejich údaje</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Zrušit" : "+ Nová firma"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <form onSubmit={handleCreate}>
            <div className="field">
              <label>IČO</label>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  value={form.ico}
                  onChange={(e) => setForm({ ...form, ico: e.target.value })}
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleAresLookup}
                  disabled={aresLoading}
                >
                  {aresLoading ? "Hledám…" : "Vyhledat v ARES"}
                </button>
              </div>
              {aresError && (
                <div style={{ fontSize: 12.5, color: "var(--danger)", marginTop: 4 }}>{aresError}</div>
              )}
              <div style={{ fontSize: 12, color: "var(--ink-400)", marginTop: 4 }}>
                Zadej IČO a klikni na "Vyhledat v ARES" - doplní název a adresu. DIČ je jen odhad,
                zkontroluj prosím jeho správnost.
              </div>
            </div>
            <div className="field">
              <label>Název firmy *</label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="field">
              <label>DIČ</label>
              <input
                value={form.dic}
                onChange={(e) => setForm({ ...form, dic: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Web</label>
              <input
                value={form.website}
                onChange={(e) => setForm({ ...form, website: e.target.value })}
                placeholder="např. nauhel.cz"
              />
            </div>
            <div className="field">
              <label>Adresa</label>
              <input
                value={form.address}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
              />
            </div>
            <button className="btn btn-primary" type="submit" disabled={saving}>
              {saving ? "Ukládám…" : "Uložit firmu"}
            </button>
          </form>
        </div>
      )}

      {loading ? (
        <div className="empty-state">Načítám…</div>
      ) : companies.length === 0 ? (
        <div className="empty-state">Zatím žádné firmy. Přidej první přes tlačítko výše.</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Název</th>
              <th>IČO</th>
              <th>Adresa</th>
            </tr>
          </thead>
          <tbody>
            {companies.map((c) => (
              <tr
                key={c.id}
                className="clickable"
                onClick={() => (window.location.href = `/companies/${c.id}`)}
              >
                <td style={{ fontWeight: 600 }}>{c.name}</td>
                <td className="mono">{c.ico || "—"}</td>
                <td>{c.address || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </ProtectedShell>
  );
}
