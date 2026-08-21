"use client";

import { useEffect, useState } from "react";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";

const emptySpeciesForm = {
  name: "",
  width_mm: "",
  width_effective_mm: "",
  length_mm: "",
  thickness_mm: "",
  purchase_price_per_m2: "",
  supplier: "",
  notes: "",
};

export default function SettingsPage() {
  const [species, setSpecies] = useState([]);
  const [parameters, setParameters] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const [showSpeciesForm, setShowSpeciesForm] = useState(false);
  const [speciesForm, setSpeciesForm] = useState(emptySpeciesForm);
  const [editingSpeciesId, setEditingSpeciesId] = useState(null);

  const [editingParamKey, setEditingParamKey] = useState(null);
  const [editParamValue, setEditParamValue] = useState("");

  function loadAll() {
    setLoading(true);
    Promise.all([api.get("/wood-species"), api.get("/pricing-parameters")])
      .then(([s, p]) => {
        setSpecies(s);
        setParameters(p);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(loadAll, []);

  async function handleCreateSpecies(e) {
    e.preventDefault();
    setError("");
    try {
      const payload = {
        name: speciesForm.name,
        width_mm: speciesForm.width_mm ? Number(speciesForm.width_mm) : null,
        width_effective_mm: speciesForm.width_effective_mm ? Number(speciesForm.width_effective_mm) : null,
        length_mm: speciesForm.length_mm ? Number(speciesForm.length_mm) : null,
        thickness_mm: speciesForm.thickness_mm ? Number(speciesForm.thickness_mm) : null,
        purchase_price_per_m2: speciesForm.purchase_price_per_m2 ? Number(speciesForm.purchase_price_per_m2) : null,
        supplier: speciesForm.supplier || null,
        notes: speciesForm.notes || null,
      };
      if (editingSpeciesId) {
        await api.put(`/wood-species/${editingSpeciesId}`, payload);
      } else {
        await api.post("/wood-species", payload);
      }
      setSpeciesForm(emptySpeciesForm);
      setShowSpeciesForm(false);
      setEditingSpeciesId(null);
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  function startEditSpecies(s) {
    setEditingSpeciesId(s.id);
    setSpeciesForm({
      name: s.name,
      width_mm: s.width_mm ?? "",
      width_effective_mm: s.width_effective_mm ?? "",
      length_mm: s.length_mm ?? "",
      thickness_mm: s.thickness_mm ?? "",
      purchase_price_per_m2: s.purchase_price_per_m2 ?? "",
      supplier: s.supplier || "",
      notes: s.notes || "",
    });
    setShowSpeciesForm(true);
  }

  async function handleDeleteSpecies(id, name) {
    if (!window.confirm(`Smazat dřevinu "${name}"?`)) return;
    setError("");
    try {
      await api.delete(`/wood-species/${id}`);
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  function startEditParam(param) {
    setEditingParamKey(param.key);
    setEditParamValue(String(param.value));
  }

  async function handleSaveParam(key) {
    setError("");
    try {
      await api.put(`/pricing-parameters/${key}`, { value: Number(editParamValue) });
      setEditingParamKey(null);
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <ProtectedShell>
      <h1 className="page-title">Nastavení</h1>
      <p className="page-subtitle">Konfigurace dřevin a cenových parametrů pro kalkulace</p>

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="empty-state">Načítám…</div>}

      {!loading && (
        <>
          <div className="card" style={{ marginBottom: 24 }}>
            <div style={{ fontWeight: 600, marginBottom: 12 }}>Cenové parametry</div>
            <div style={{ fontSize: 12.5, color: "var(--ink-600)", marginBottom: 14 }}>
              Výchozí sazby pro rychlé předvyplnění položek kalkulace (marže, doprava, příplatky
              produktových řad). Nemění existující kalkulace zpětně.
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Parametr</th>
                  <th>Hodnota</th>
                  <th>Jednotka</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {parameters.map((p) => (
                  <tr key={p.key}>
                    <td>{p.label}</td>
                    <td className="mono">
                      {editingParamKey === p.key ? (
                        <input
                          type="number"
                          step="0.0001"
                          value={editParamValue}
                          onChange={(e) => setEditParamValue(e.target.value)}
                          style={{ width: 120, padding: "4px 6px", fontSize: 13 }}
                        />
                      ) : (
                        Number(p.value)
                      )}
                    </td>
                    <td style={{ color: "var(--ink-600)" }}>{p.unit || "—"}</td>
                    <td>
                      {editingParamKey === p.key ? (
                        <>
                          <button
                            className="btn btn-primary"
                            style={{ padding: "3px 8px", fontSize: 11.5, marginRight: 4 }}
                            onClick={() => handleSaveParam(p.key)}
                          >
                            Uložit
                          </button>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: "3px 8px", fontSize: 11.5 }}
                            onClick={() => setEditingParamKey(null)}
                          >
                            Zrušit
                          </button>
                        </>
                      ) : (
                        <button
                          className="btn btn-secondary"
                          style={{ padding: "3px 8px", fontSize: 11.5 }}
                          onClick={() => startEditParam(p)}
                        >
                          Upravit
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ fontWeight: 600 }}>Dřeviny</div>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setShowSpeciesForm(!showSpeciesForm);
                  setEditingSpeciesId(null);
                  setSpeciesForm(emptySpeciesForm);
                }}
              >
                {showSpeciesForm ? "Zrušit" : "+ Nová dřevina"}
              </button>
            </div>

            {showSpeciesForm && (
              <form
                onSubmit={handleCreateSpecies}
                style={{ marginBottom: 16, paddingBottom: 16, borderBottom: "1px solid var(--paper-200)" }}
              >
                <div className="field">
                  <label>Název *</label>
                  <input
                    required
                    value={speciesForm.name}
                    onChange={(e) => setSpeciesForm({ ...speciesForm, name: e.target.value })}
                    placeholder='např. Smrk "KLASIK" 20x146 mm, délka 4000mm'
                  />
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 8 }}>
                  <div className="field">
                    <label>Šířka (mm)</label>
                    <input
                      type="number"
                      value={speciesForm.width_mm}
                      onChange={(e) => setSpeciesForm({ ...speciesForm, width_mm: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label>Šířka eff. (mm)</label>
                    <input
                      type="number"
                      value={speciesForm.width_effective_mm}
                      onChange={(e) => setSpeciesForm({ ...speciesForm, width_effective_mm: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label>Délka (mm)</label>
                    <input
                      type="number"
                      value={speciesForm.length_mm}
                      onChange={(e) => setSpeciesForm({ ...speciesForm, length_mm: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label>Tloušťka (mm)</label>
                    <input
                      type="number"
                      value={speciesForm.thickness_mm}
                      onChange={(e) => setSpeciesForm({ ...speciesForm, thickness_mm: e.target.value })}
                    />
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  <div className="field">
                    <label>Nákupní cena/m² bez DPH (Kč)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={speciesForm.purchase_price_per_m2}
                      onChange={(e) => setSpeciesForm({ ...speciesForm, purchase_price_per_m2: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label>Dodavatel</label>
                    <input
                      value={speciesForm.supplier}
                      onChange={(e) => setSpeciesForm({ ...speciesForm, supplier: e.target.value })}
                    />
                  </div>
                </div>
                <button className="btn btn-primary" type="submit">
                  {editingSpeciesId ? "Uložit změny" : "Vytvořit dřevinu"}
                </button>
              </form>
            )}

            {species.length === 0 ? (
              <div style={{ fontSize: 13.5, color: "var(--ink-400)" }}>Zatím žádné dřeviny</div>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Název</th>
                    <th>Rozměry (Š×T, délka)</th>
                    <th>Cena/m² bez DPH</th>
                    <th>Dodavatel</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {species.map((s) => (
                    <tr key={s.id}>
                      <td style={{ fontWeight: 600 }}>{s.name}</td>
                      <td className="mono" style={{ fontSize: 12.5 }}>
                        {s.width_mm ? `${Number(s.width_mm)}×${Number(s.thickness_mm)} mm` : "—"}
                        {s.length_mm ? `, ${Number(s.length_mm)} mm` : ""}
                      </td>
                      <td className="mono">
                        {s.purchase_price_per_m2 ? Number(s.purchase_price_per_m2).toLocaleString("cs-CZ") + " Kč" : "—"}
                      </td>
                      <td>{s.supplier || "—"}</td>
                      <td style={{ whiteSpace: "nowrap" }}>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: "3px 8px", fontSize: 11.5, marginRight: 4 }}
                          onClick={() => startEditSpecies(s)}
                        >
                          Upravit
                        </button>
                        <button
                          className="btn btn-danger"
                          style={{ padding: "3px 8px", fontSize: 11.5 }}
                          onClick={() => handleDeleteSpecies(s.id, s.name)}
                        >
                          Smazat
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </ProtectedShell>
  );
}
