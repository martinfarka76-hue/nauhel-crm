"use client";

import { useEffect, useState } from "react";
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

export default function ContactsPage() {
  const [contacts, setContacts] = useState([]);
  const [companies, setCompanies] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    Promise.all([api.get("/contacts"), api.get("/companies")])
      .then(([contactsData, companiesData]) => {
        setContacts(contactsData);
        const map = {};
        companiesData.forEach((c) => (map[c.id] = c));
        setCompanies(map);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

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
      <h1 className="page-title">Kontakty</h1>
      <p className="page-subtitle">Kontaktní osoby napříč všemi firmami</p>

      {error && <div className="error-banner">{error}</div>}

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
          Zatím žádné kontakty. Přidej je na detailu firmy.
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
                  onClick={() => company && (window.location.href = `/companies/${company.id}`)}
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
