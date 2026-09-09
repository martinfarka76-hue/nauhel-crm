"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";

function getDomain(url) {
  if (!url) return null;
  try {
    let u = url.trim();
    if (!/^https?:\/\//i.test(u)) u = "https://" + u;
    return new URL(u).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

function CompanyAvatar({ name, website }) {
  const domain = getDomain(website);
  const initial = name ? name.charAt(0).toUpperCase() : "?";
  const [imgFailed, setImgFailed] = useState(false);

  if (domain && !imgFailed) {
    return (
      <img
        src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`}
        alt=""
        onError={() => setImgFailed(true)}
        style={{
          width: 20,
          height: 20,
          borderRadius: "50%",
          flexShrink: 0,
          objectFit: "cover",
          background: "var(--paper-100)",
          border: "1px solid var(--paper-200)",
        }}
      />
    );
  }
  return (
    <span
      style={{
        width: 20,
        height: 20,
        borderRadius: "50%",
        flexShrink: 0,
        background: "var(--ember-500)",
        color: "#fff",
        fontSize: 9.5,
        fontWeight: 700,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {initial}
    </span>
  );
}

const emptyNewContactForm = { company_id: "", first_name: "", last_name: "", email: "", phone: "", position: "" };

export default function ContactsPage() {
  const router = useRouter();
  const [contacts, setContacts] = useState([]);
  const [companies, setCompanies] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [showContactForm, setShowContactForm] = useState(false);
  const [newContactForm, setNewContactForm] = useState(emptyNewContactForm);
  const [creatingNewCompany, setCreatingNewCompany] = useState(false);
  const [newCompanyForm, setNewCompanyForm] = useState({ name: "", ico: "", dic: "", website: "", address: "" });
  const [aresLoading, setAresLoading] = useState(false);
  const [aresError, setAresError] = useState("");
  const [saving, setSaving] = useState(false);

  function loadAll() {
    setLoading(true);
    Promise.all([api.get("/contacts"), api.get("/companies")])
      .then(([contactsData, companiesData]) => {
        setContacts(contactsData);
        const map = {};
        companiesData.forEach((c) => (map[c.id] = c));
        setCompanies(map);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(loadAll, []);

  async function handleAresLookup() {
    if (!newCompanyForm.ico) {
      setAresError("Nejdřív vyplň IČO.");
      return;
    }
    setAresLoading(true);
    setAresError("");
    try {
      const result = await api.get(`/ares/${newCompanyForm.ico}`);
      setNewCompanyForm({
        ...newCompanyForm,
        name: result.name || newCompanyForm.name,
        address: result.address || newCompanyForm.address,
        dic: result.dic_guess || newCompanyForm.dic,
      });
    } catch (err) {
      setAresError(err.message);
    } finally {
      setAresLoading(false);
    }
  }

  async function handleCreateContact(e) {
    e.preventDefault();
    if (!creatingNewCompany && !newContactForm.company_id) {
      setError("Vyber prosím firmu.");
      return;
    }
    if (creatingNewCompany && !newCompanyForm.name.trim()) {
      setError("Vyplň prosím název nové firmy.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      let companyId = newContactForm.company_id;
      if (creatingNewCompany) {
        const newCompany = await api.post("/companies", newCompanyForm);
        companyId = newCompany.id;
      }
      await api.post("/contacts", { ...newContactForm, company_id: companyId });
      setNewContactForm(emptyNewContactForm);
      setCreatingNewCompany(false);
      setNewCompanyForm({ name: "", ico: "", dic: "", website: "", address: "" });
      setShowContactForm(false);
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const filteredContacts = contacts.filter((c) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.trim().toLowerCase();
    const company = companies[c.company_id];
    return (
      `${c.first_name} ${c.last_name}`.toLowerCase().includes(q) ||
      (c.email || "").toLowerCase().includes(q) ||
      (c.phone || "").toLowerCase().includes(q) ||
      (company ? company.name.toLowerCase().includes(q) : false)
    );
  });

  return (
    <ProtectedShell>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 className="page-title">Kontakty</h1>
          <p className="page-subtitle">Kontaktní osoby napříč všemi firmami</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => {
            setShowContactForm(!showContactForm);
            setNewContactForm(emptyNewContactForm);
            setCreatingNewCompany(false);
            setNewCompanyForm({ name: "", ico: "", dic: "", website: "", address: "" });
          }}
        >
          {showContactForm ? "Zrušit" : "+ Nový kontakt"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {showContactForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <form onSubmit={handleCreateContact}>
            <div className="field">
              <label>Firma *</label>
              {creatingNewCompany ? (
                <div
                  style={{
                    background: "var(--paper-50)",
                    border: "1px solid var(--paper-200)",
                    borderRadius: 8,
                    padding: "12px 14px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "var(--ink-600)" }}>Nová firma</div>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ padding: "3px 8px", fontSize: 11.5 }}
                      onClick={() => {
                        setCreatingNewCompany(false);
                        setNewCompanyForm({ name: "", ico: "", dic: "", website: "", address: "" });
                      }}
                    >
                      Zrušit
                    </button>
                  </div>

                  <div className="field">
                    <label>IČO</label>
                    <div style={{ display: "flex", gap: 8 }}>
                      <input
                        value={newCompanyForm.ico}
                        onChange={(e) => setNewCompanyForm({ ...newCompanyForm, ico: e.target.value })}
                        style={{ flex: 1 }}
                      />
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ whiteSpace: "nowrap" }}
                        onClick={handleAresLookup}
                        disabled={aresLoading}
                      >
                        {aresLoading ? "Hledám…" : "Vyhledat v ARES"}
                      </button>
                    </div>
                    {aresError && (
                      <div style={{ fontSize: 12.5, color: "var(--danger)", marginTop: 4 }}>{aresError}</div>
                    )}
                    <div style={{ fontSize: 11.5, color: "var(--ink-400)", marginTop: 4 }}>
                      Zadej IČO a klikni na "Vyhledat v ARES" - doplní název a adresu. DIČ je jen odhad,
                      zkontroluj prosím jeho správnost.
                    </div>
                  </div>
                  <div className="field">
                    <label>Název firmy *</label>
                    <input
                      required
                      autoFocus
                      value={newCompanyForm.name}
                      onChange={(e) => setNewCompanyForm({ ...newCompanyForm, name: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label>DIČ</label>
                    <input
                      value={newCompanyForm.dic}
                      onChange={(e) => setNewCompanyForm({ ...newCompanyForm, dic: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label>Web</label>
                    <input
                      value={newCompanyForm.website}
                      onChange={(e) => setNewCompanyForm({ ...newCompanyForm, website: e.target.value })}
                      placeholder="např. nauhel.cz"
                    />
                  </div>
                  <div className="field" style={{ marginBottom: 0 }}>
                    <label>Adresa</label>
                    <input
                      value={newCompanyForm.address}
                      onChange={(e) => setNewCompanyForm({ ...newCompanyForm, address: e.target.value })}
                    />
                  </div>
                </div>
              ) : (
                <select
                  required
                  value={newContactForm.company_id}
                  onChange={(e) => {
                    if (e.target.value === "__new__") {
                      setCreatingNewCompany(true);
                    } else {
                      setNewContactForm({ ...newContactForm, company_id: e.target.value });
                    }
                  }}
                >
                  <option value="" disabled>
                    — vyber firmu —
                  </option>
                  <option value="__new__" style={{ color: "var(--ember-600)", fontWeight: 600 }}>
                    + Vytvořit novou firmu…
                  </option>
                  {Object.values(companies)
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                </select>
              )}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <div className="field">
                <label>Jméno *</label>
                <input
                  required
                  value={newContactForm.first_name}
                  onChange={(e) => setNewContactForm({ ...newContactForm, first_name: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Příjmení *</label>
                <input
                  required
                  value={newContactForm.last_name}
                  onChange={(e) => setNewContactForm({ ...newContactForm, last_name: e.target.value })}
                />
              </div>
            </div>
            <div className="field">
              <label>Email</label>
              <input
                type="email"
                value={newContactForm.email}
                onChange={(e) => setNewContactForm({ ...newContactForm, email: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Telefon</label>
              <input
                value={newContactForm.phone}
                onChange={(e) => setNewContactForm({ ...newContactForm, phone: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Pozice</label>
              <input
                value={newContactForm.position}
                onChange={(e) => setNewContactForm({ ...newContactForm, position: e.target.value })}
              />
            </div>
            <button className="btn btn-primary" type="submit" disabled={saving}>
              {saving ? "Ukládám…" : "Uložit kontakt"}
            </button>
          </form>
        </div>
      )}

      {!loading && contacts.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <input
            type="text"
            placeholder="Hledat podle jména, emailu, telefonu nebo firmy…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: "8px 12px",
              fontSize: 13,
              borderRadius: 8,
              border: "1px solid var(--paper-200)",
              width: 340,
            }}
          />
        </div>
      )}

      {loading ? (
        <div className="empty-state">Načítám…</div>
      ) : contacts.length === 0 ? (
        <div className="empty-state">
          Zatím žádné kontakty. Přidej první tlačítkem "+ Nový kontakt" nahoře.
        </div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Jméno</th>
              <th>Pozice</th>
              <th>Email</th>
              <th>Telefon</th>
              <th>Firma</th>
            </tr>
          </thead>
          <tbody>
            {filteredContacts.map((c) => {
              const company = companies[c.company_id];
              return (
                <tr
                  key={c.id}
                  className="clickable"
                  onClick={() => company && router.push(`/companies/${company.id}`)}
                >
                  <td style={{ fontWeight: 600 }}>
                    {c.first_name} {c.last_name}
                  </td>
                  <td>{c.position || "—"}</td>
                  <td>{c.email || "—"}</td>
                  <td className="mono">{c.phone || "—"}</td>
                  <td>
                    {company ? (
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <CompanyAvatar name={company.name} website={company.website} />
                        {company.name}
                      </div>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </ProtectedShell>
  );
}
