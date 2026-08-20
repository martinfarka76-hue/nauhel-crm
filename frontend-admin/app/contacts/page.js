"use client";

import { useEffect, useState } from "react";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";

export default function ContactsPage() {
  const [contacts, setContacts] = useState([]);
  const [companies, setCompanies] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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

  return (
    <ProtectedShell>
      <h1 className="page-title">Kontakty</h1>
      <p className="page-subtitle">Kontaktní osoby napříč všemi firmami</p>

      {error && <div className="error-banner">{error}</div>}

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
            {contacts.map((c) => {
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
                  <td>{company ? company.name : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </ProtectedShell>
  );
}
