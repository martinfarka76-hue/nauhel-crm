"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";
import { STATUS_COLORS } from "@/lib/constants";

const emptyContactForm = { first_name: "", last_name: "", email: "", phone: "", position: "" };
const PUBLIC_URL = process.env.NEXT_PUBLIC_PUBLIC_URL || "http://localhost:18082";

function formatDate(iso) {
  if (!iso) return "—";
  const utcIso = iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z";
  return new Date(utcIso).toLocaleString("cs-CZ");
}

export default function CompanyDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [company, setCompany] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [deals, setDeals] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [error, setError] = useState("");
  const [copiedId, setCopiedId] = useState(null);

  const [partnerPrices, setPartnerPrices] = useState([]);
  const [showPartnerPriceForm, setShowPartnerPriceForm] = useState(false);
  const [editingPartnerPriceId, setEditingPartnerPriceId] = useState(null);
  const [partnerPriceForm, setPartnerPriceForm] = useState({
    name: "",
    wood_type: "",
    dimensions: "",
    profile: "",
    length: "",
    surface: "",
    service_price_per_m2: "",
  });

  const [showDealForm, setShowDealForm] = useState(false);
  const [dealForm, setDealForm] = useState({
    name: "",
    price: "",
    expected_close_date: "",
    expected_invoice_date: "",
  });
  const [saving, setSaving] = useState(false);
  const [aresRefreshLoading, setAresRefreshLoading] = useState(false);
  const [aresRefreshError, setAresRefreshError] = useState("");

  const [editingCompany, setEditingCompany] = useState(false);
  const [companyForm, setCompanyForm] = useState(null);

  const [showContactForm, setShowContactForm] = useState(false);
  const [newContactForm, setNewContactForm] = useState(emptyContactForm);
  const [editingContactId, setEditingContactId] = useState(null);
  const [editContactForm, setEditContactForm] = useState(emptyContactForm);

  function loadAll() {
    Promise.all([
      api.get(`/companies/${id}`),
      api.get(`/contacts?company_id=${id}`),
      api.get(`/deals?company_id=${id}`),
      api.get(`/documents?company_id=${id}`),
      api.get(`/partner-price-items?company_id=${id}`),
    ])
      .then(([c, ct, d, docs, pp]) => {
        setCompany(c);
        setContacts(ct);
        setDeals(d);
        setDocuments(docs);
        setPartnerPrices(pp);
      })
      .catch((err) => setError(err.message));
  }

  useEffect(loadAll, [id]);

  function handleCopyLink(accessToken, docId) {
    const url = `${PUBLIC_URL}/n/${accessToken}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopiedId(docId);
      setTimeout(() => setCopiedId(null), 2000);
    });
  }

  function dealNameFor(dealId) {
    const deal = deals.find((d) => d.id === dealId);
    return deal ? deal.name : "—";
  }

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
        expected_close_date: dealForm.expected_close_date || null,
        expected_invoice_date: dealForm.expected_invoice_date || null,
      });
      setDealForm({ name: "", price: "", expected_close_date: "", expected_invoice_date: "" });
      setShowDealForm(false);
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  // --- Firma: editace a mazání ---

  function startEditCompany() {
    setCompanyForm({
      name: company.name,
      ico: company.ico || "",
      dic: company.dic || "",
      website: company.website || "",
      address: company.address || "",
      notes: company.notes || "",
      is_partner: company.is_partner || false,
    });
    setEditingCompany(true);
  }

  async function handleSaveCompany(e) {
    e.preventDefault();
    setError("");
    try {
      await api.put(`/companies/${id}`, companyForm);
      setEditingCompany(false);
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  const emptyPartnerPriceForm = {
    name: "",
    wood_type: "",
    dimensions: "",
    profile: "",
    length: "",
    surface: "",
    service_price_per_m2: "",
  };

  function startEditPartnerPrice(item) {
    setPartnerPriceForm({
      name: item.name,
      wood_type: item.wood_type || "",
      dimensions: item.dimensions || "",
      profile: item.profile || "",
      length: item.length || "",
      surface: item.surface || "",
      service_price_per_m2: String(item.service_price_per_m2),
    });
    setEditingPartnerPriceId(item.id);
    setShowPartnerPriceForm(true);
  }

  async function handleSavePartnerPrice(e) {
    e.preventDefault();
    setError("");
    const payload = {
      ...partnerPriceForm,
      service_price_per_m2: Number(partnerPriceForm.service_price_per_m2),
    };
    try {
      if (editingPartnerPriceId) {
        await api.put(`/partner-price-items/${editingPartnerPriceId}`, payload);
      } else {
        await api.post("/partner-price-items", { ...payload, company_id: id });
      }
      setShowPartnerPriceForm(false);
      setEditingPartnerPriceId(null);
      setPartnerPriceForm(emptyPartnerPriceForm);
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeletePartnerPrice(itemId) {
    if (!window.confirm("Opravdu smazat tuto položku ceníku?")) return;
    try {
      await api.delete(`/partner-price-items/${itemId}`);
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAresRefresh() {
    if (!companyForm.ico) {
      setAresRefreshError("Nejdřív vyplň IČO.");
      return;
    }
    setAresRefreshLoading(true);
    setAresRefreshError("");
    try {
      const result = await api.get(`/ares/${companyForm.ico}`);
      setCompanyForm({
        ...companyForm,
        name: result.name || companyForm.name,
        address: result.address || companyForm.address,
        dic: result.dic_guess || companyForm.dic,
      });
    } catch (err) {
      setAresRefreshError(err.message);
    } finally {
      setAresRefreshLoading(false);
    }
  }

  async function handleDeleteCompany() {
    if (!window.confirm(`Opravdu smazat firmu "${company.name}"? Tato akce je nevratná.`)) return;
    setError("");
    try {
      await api.delete(`/companies/${id}`);
      router.push("/companies");
    } catch (err) {
      setError(err.message);
    }
  }

  // --- Kontakty: vytvoření, editace, mazání ---

  async function handleCreateContact(e) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/contacts", { company_id: id, ...newContactForm });
      setNewContactForm(emptyContactForm);
      setShowContactForm(false);
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  function startEditContact(contact) {
    setEditingContactId(contact.id);
    setEditContactForm({
      first_name: contact.first_name,
      last_name: contact.last_name,
      email: contact.email || "",
      phone: contact.phone || "",
      position: contact.position || "",
    });
  }

  async function handleSaveContact(contactId) {
    setError("");
    try {
      await api.put(`/contacts/${contactId}`, editContactForm);
      setEditingContactId(null);
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteContact(contactId, contactName) {
    if (!window.confirm(`Opravdu smazat kontakt "${contactName}"?`)) return;
    setError("");
    try {
      await api.delete(`/contacts/${contactId}`);
      loadAll();
    } catch (err) {
      setError(err.message);
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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 className="page-title" style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {company.name}
            {company.is_partner && (
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                  color: "var(--ember-600)",
                  background: "var(--ember-500)15",
                  border: "1px solid var(--ember-500)",
                  borderRadius: 6,
                  padding: "3px 8px",
                }}
              >
                Partner
              </span>
            )}
          </h1>
          <p className="page-subtitle">
            {company.ico ? `IČO ${company.ico}` : ""} {company.dic ? `· DIČ ${company.dic}` : ""}
          </p>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 28 }}>
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <div style={{ fontWeight: 600 }}>Údaje o firmě</div>
            {!editingCompany && (
              <div style={{ display: "flex", gap: 6 }}>
                <button
                  className="btn btn-secondary"
                  style={{ padding: "4px 10px", fontSize: 12.5 }}
                  onClick={startEditCompany}
                >
                  Upravit
                </button>
                <button
                  className="btn btn-danger"
                  style={{ padding: "4px 10px", fontSize: 12.5 }}
                  onClick={handleDeleteCompany}
                >
                  Smazat
                </button>
              </div>
            )}
          </div>

          {editingCompany ? (
            <form onSubmit={handleSaveCompany}>
              <div className="field">
                <label>Název firmy</label>
                <input
                  required
                  value={companyForm.name}
                  onChange={(e) => setCompanyForm({ ...companyForm, name: e.target.value })}
                />
              </div>
              <div className="field">
                <label>IČO</label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    value={companyForm.ico}
                    onChange={(e) => setCompanyForm({ ...companyForm, ico: e.target.value })}
                    style={{ flex: 1 }}
                  />
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleAresRefresh}
                    disabled={aresRefreshLoading}
                    style={{ whiteSpace: "nowrap" }}
                  >
                    {aresRefreshLoading ? "Načítám…" : "Načíst z ARES"}
                  </button>
                </div>
                {aresRefreshError && (
                  <div style={{ fontSize: 12.5, color: "var(--danger)", marginTop: 4 }}>{aresRefreshError}</div>
                )}
                <div style={{ fontSize: 11.5, color: "var(--ink-400)", marginTop: 4 }}>
                  Doplní název/adresu/DIČ podle ARES - zkontroluj a ulož tlačítkem níže.
                </div>
              </div>
              <div className="field">
                <label>DIČ</label>
                <input
                  value={companyForm.dic}
                  onChange={(e) => setCompanyForm({ ...companyForm, dic: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Web</label>
                <input
                  value={companyForm.website}
                  onChange={(e) => setCompanyForm({ ...companyForm, website: e.target.value })}
                  placeholder="např. nauhel.cz"
                />
              </div>
              <div className="field">
                <label>Adresa</label>
                <input
                  value={companyForm.address}
                  onChange={(e) => setCompanyForm({ ...companyForm, address: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Poznámky</label>
                <input
                  value={companyForm.notes}
                  onChange={(e) => setCompanyForm({ ...companyForm, notes: e.target.value })}
                />
              </div>
              <div className="field">
                <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={companyForm.is_partner}
                    onChange={(e) => setCompanyForm({ ...companyForm, is_partner: e.target.checked })}
                  />
                  Partner (dodává vlastní dřevo, fakturujeme jen službu)
                </label>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn btn-primary" type="submit">
                  Uložit
                </button>
                <button className="btn btn-secondary" type="button" onClick={() => setEditingCompany(false)}>
                  Zrušit
                </button>
              </div>
            </form>
          ) : (
            <div style={{ fontSize: 13.5, color: "var(--ink-600)", lineHeight: 1.8 }}>
              <div>Adresa: {company.address || "—"}</div>
              <div>Poznámky: {company.notes || "—"}</div>
            </div>
          )}
        </div>

        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <div style={{ fontWeight: 600 }}>Kontaktní osoby</div>
            <button
              className="btn btn-secondary"
              style={{ padding: "4px 10px", fontSize: 12.5 }}
              onClick={() => setShowContactForm(!showContactForm)}
            >
              {showContactForm ? "Zrušit" : "+ Nový kontakt"}
            </button>
          </div>

          {showContactForm && (
            <form
              onSubmit={handleCreateContact}
              style={{ marginBottom: 12, paddingBottom: 12, borderBottom: "1px solid var(--paper-200)" }}
            >
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <div className="field" style={{ marginBottom: 8 }}>
                  <label>Jméno *</label>
                  <input
                    required
                    value={newContactForm.first_name}
                    onChange={(e) => setNewContactForm({ ...newContactForm, first_name: e.target.value })}
                  />
                </div>
                <div className="field" style={{ marginBottom: 8 }}>
                  <label>Příjmení *</label>
                  <input
                    required
                    value={newContactForm.last_name}
                    onChange={(e) => setNewContactForm({ ...newContactForm, last_name: e.target.value })}
                  />
                </div>
              </div>
              <div className="field" style={{ marginBottom: 8 }}>
                <label>Email</label>
                <input
                  type="email"
                  value={newContactForm.email}
                  onChange={(e) => setNewContactForm({ ...newContactForm, email: e.target.value })}
                />
              </div>
              <div className="field" style={{ marginBottom: 8 }}>
                <label>Telefon</label>
                <input
                  value={newContactForm.phone}
                  onChange={(e) => setNewContactForm({ ...newContactForm, phone: e.target.value })}
                />
              </div>
              <div className="field" style={{ marginBottom: 8 }}>
                <label>Pozice</label>
                <input
                  value={newContactForm.position}
                  onChange={(e) => setNewContactForm({ ...newContactForm, position: e.target.value })}
                />
              </div>
              <button className="btn btn-primary" type="submit">
                Uložit kontakt
              </button>
            </form>
          )}

          {contacts.length === 0 ? (
            <div style={{ fontSize: 13.5, color: "var(--ink-400)" }}>Zatím žádné kontakty</div>
          ) : (
            contacts.map((c) =>
              editingContactId === c.id ? (
                <form
                  key={c.id}
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSaveContact(c.id);
                  }}
                  style={{ marginBottom: 10, paddingBottom: 10, borderBottom: "1px solid var(--paper-200)" }}
                >
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    <input
                      value={editContactForm.first_name}
                      onChange={(e) => setEditContactForm({ ...editContactForm, first_name: e.target.value })}
                      style={{ fontSize: 13, padding: "5px 8px" }}
                    />
                    <input
                      value={editContactForm.last_name}
                      onChange={(e) => setEditContactForm({ ...editContactForm, last_name: e.target.value })}
                      style={{ fontSize: 13, padding: "5px 8px" }}
                    />
                  </div>
                  <input
                    value={editContactForm.email}
                    onChange={(e) => setEditContactForm({ ...editContactForm, email: e.target.value })}
                    placeholder="email"
                    style={{ fontSize: 13, padding: "5px 8px", width: "100%", marginTop: 6 }}
                  />
                  <input
                    value={editContactForm.phone}
                    onChange={(e) => setEditContactForm({ ...editContactForm, phone: e.target.value })}
                    placeholder="telefon"
                    style={{ fontSize: 13, padding: "5px 8px", width: "100%", marginTop: 6 }}
                  />
                  <input
                    value={editContactForm.position}
                    onChange={(e) => setEditContactForm({ ...editContactForm, position: e.target.value })}
                    placeholder="pozice"
                    style={{ fontSize: 13, padding: "5px 8px", width: "100%", marginTop: 6, marginBottom: 8 }}
                  />
                  <div style={{ display: "flex", gap: 6 }}>
                    <button className="btn btn-primary" style={{ padding: "4px 10px", fontSize: 12.5 }} type="submit">
                      Uložit
                    </button>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: "4px 10px", fontSize: 12.5 }}
                      type="button"
                      onClick={() => setEditingContactId(null)}
                    >
                      Zrušit
                    </button>
                  </div>
                </form>
              ) : (
                <div key={c.id} style={{ fontSize: 13.5, marginBottom: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <div>
                      <strong>
                        {c.first_name} {c.last_name}
                      </strong>
                      {c.position ? ` — ${c.position}` : ""}
                      <div style={{ color: "var(--ink-600)" }}>{c.email} {c.phone}</div>
                    </div>
                    <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: "3px 8px", fontSize: 11.5 }}
                        onClick={() => startEditContact(c)}
                      >
                        Upravit
                      </button>
                      <button
                        className="btn btn-danger"
                        style={{ padding: "3px 8px", fontSize: 11.5 }}
                        onClick={() => handleDeleteContact(c.id, `${c.first_name} ${c.last_name}`)}
                      >
                        Smazat
                      </button>
                    </div>
                  </div>
                </div>
              )
            )
          )}
        </div>
      </div>

      {company.is_partner && (
        <div className="card" style={{ marginBottom: 28 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <div style={{ fontWeight: 600 }}>Ceník partnera</div>
            <button
              className="btn btn-secondary"
              style={{ padding: "4px 10px", fontSize: 12.5 }}
              onClick={() => {
                setShowPartnerPriceForm(!showPartnerPriceForm);
                setEditingPartnerPriceId(null);
                setPartnerPriceForm(emptyPartnerPriceForm);
              }}
            >
              {showPartnerPriceForm ? "Zrušit" : "+ Nová položka"}
            </button>
          </div>
          <div style={{ fontSize: 12, color: "var(--ink-600)", marginBottom: 12 }}>
            Cena služby bez dopravy bez DPH za m² - partner dodává vlastní dřevo, fakturuje se jen opálení/úprava.
          </div>

          {showPartnerPriceForm && (
            <form
              onSubmit={handleSavePartnerPrice}
              style={{ marginBottom: 14, paddingBottom: 14, borderBottom: "1px solid var(--paper-200)" }}
            >
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                <div className="field">
                  <label>Název *</label>
                  <input
                    required
                    value={partnerPriceForm.name}
                    onChange={(e) => setPartnerPriceForm({ ...partnerPriceForm, name: e.target.value })}
                    placeholder="např. Atacama - STANDARD"
                  />
                </div>
                <div className="field">
                  <label>Dřevina</label>
                  <input
                    value={partnerPriceForm.wood_type}
                    onChange={(e) => setPartnerPriceForm({ ...partnerPriceForm, wood_type: e.target.value })}
                    placeholder="Borovice / Modřín"
                  />
                </div>
                <div className="field">
                  <label>Rozměr (mm)</label>
                  <input
                    value={partnerPriceForm.dimensions}
                    onChange={(e) => setPartnerPriceForm({ ...partnerPriceForm, dimensions: e.target.value })}
                    placeholder="20x145"
                  />
                </div>
                <div className="field">
                  <label>Profil</label>
                  <input
                    value={partnerPriceForm.profile}
                    onChange={(e) => setPartnerPriceForm({ ...partnerPriceForm, profile: e.target.value })}
                    placeholder="Falcovaný (Z)"
                  />
                </div>
                <div className="field">
                  <label>Délka (m)</label>
                  <input
                    value={partnerPriceForm.length}
                    onChange={(e) => setPartnerPriceForm({ ...partnerPriceForm, length: e.target.value })}
                    placeholder="3/4/5"
                  />
                </div>
                <div className="field">
                  <label>Cena služby/m² bez DPH *</label>
                  <input
                    required
                    type="number"
                    step="0.01"
                    value={partnerPriceForm.service_price_per_m2}
                    onChange={(e) => setPartnerPriceForm({ ...partnerPriceForm, service_price_per_m2: e.target.value })}
                  />
                </div>
              </div>
              <div className="field">
                <label>Povrch</label>
                <input
                  value={partnerPriceForm.surface}
                  onChange={(e) => setPartnerPriceForm({ ...partnerPriceForm, surface: e.target.value })}
                  placeholder="hluboce opálený - 100% černý"
                />
              </div>
              <button className="btn btn-primary" type="submit">
                {editingPartnerPriceId ? "Uložit změny" : "Přidat položku"}
              </button>
            </form>
          )}

          {partnerPrices.length === 0 ? (
            <div style={{ fontSize: 13, color: "var(--ink-400)" }}>Zatím žádné položky ceníku.</div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Název</th>
                  <th>Dřevina / rozměr / profil</th>
                  <th>Povrch</th>
                  <th>Cena služby/m²</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {partnerPrices.map((item) => (
                  <tr key={item.id}>
                    <td style={{ fontWeight: 600 }}>{item.name}</td>
                    <td className="mono" style={{ fontSize: 12.5 }}>
                      {[item.wood_type, item.dimensions, item.profile, item.length && `${item.length} m`]
                        .filter(Boolean)
                        .join(" · ")}
                    </td>
                    <td style={{ fontSize: 12.5 }}>{item.surface || "—"}</td>
                    <td className="mono">{Number(item.service_price_per_m2).toLocaleString("cs-CZ")} Kč</td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: "3px 8px", fontSize: 12, marginRight: 6 }}
                        onClick={() => startEditPartnerPrice(item)}
                      >
                        Upravit
                      </button>
                      <button
                        className="btn btn-danger"
                        style={{ padding: "3px 8px", fontSize: 12 }}
                        onClick={() => handleDeletePartnerPrice(item.id)}
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
      )}

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
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>Odhadované uzavření</label>
                <input
                  type="date"
                  value={dealForm.expected_close_date}
                  onChange={(e) => setDealForm({ ...dealForm, expected_close_date: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Odhadovaná fakturace</label>
                <input
                  type="date"
                  value={dealForm.expected_invoice_date}
                  onChange={(e) => setDealForm({ ...dealForm, expected_invoice_date: e.target.value })}
                />
              </div>
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
              <tr key={d.id} className="clickable" onClick={() => router.push(`/deals/${d.id}`)}>
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

      <div style={{ fontWeight: 600, marginTop: 28, marginBottom: 12 }}>Dokumenty</div>
      {documents.length === 0 ? (
        <div className="empty-state">Zatím žádné dokumenty.</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Typ</th>
              <th>Obchodní případ</th>
              <th>Vytvořeno</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id}>
                <td style={{ fontWeight: 600 }}>
                  {doc.document_type} {doc.version > 1 ? `(v${doc.version})` : ""}
                </td>
                <td>
                  <a href={`/deals/${doc.deal_id}`} style={{ textDecoration: "underline" }}>
                    {dealNameFor(doc.deal_id)}
                  </a>
                </td>
                <td style={{ color: "var(--ink-600)" }}>{formatDate(doc.created_at)}</td>
                <td>
                  {(doc.document_type === "Nabídka" || doc.document_type === "Objednávka") && (
                    <button
                      className="btn btn-secondary"
                      style={{ padding: "4px 10px", fontSize: 12 }}
                      onClick={() => handleCopyLink(doc.access_token, doc.id)}
                    >
                      {copiedId === doc.id ? "Zkopírováno ✓" : "Zkopírovat odkaz"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </ProtectedShell>
  );
}
