"use client";

import { useEffect, useState } from "react";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";

const PUBLIC_URL = process.env.NEXT_PUBLIC_PUBLIC_URL || "http://localhost:18082";
const DOCUMENT_TYPES = ["Nabídka", "Objednávka", "Zálohová faktura", "Dodací list", "Finální faktura"];

function formatDate(iso) {
  if (!iso) return "—";
  const utcIso = iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z";
  return new Date(utcIso).toLocaleString("cs-CZ");
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [deals, setDeals] = useState({});
  const [companies, setCompanies] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [copiedId, setCopiedId] = useState(null);

  function loadAll(filter) {
    setLoading(true);
    const docsUrl = filter ? `/documents?document_type=${encodeURIComponent(filter)}` : "/documents";
    Promise.all([api.get(docsUrl), api.get("/deals"), api.get("/companies")])
      .then(([docs, dealsData, companiesData]) => {
        setDocuments(docs);
        const dealsMap = {};
        dealsData.forEach((d) => (dealsMap[d.id] = d));
        setDeals(dealsMap);
        const companiesMap = {};
        companiesData.forEach((c) => (companiesMap[c.id] = c.name));
        setCompanies(companiesMap);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => loadAll(typeFilter), [typeFilter]);

  function handleCopyLink(accessToken, docId) {
    const url = `${PUBLIC_URL}/n/${accessToken}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopiedId(docId);
      setTimeout(() => setCopiedId(null), 2000);
    });
  }

  function companyNameForDeal(dealId) {
    const deal = deals[dealId];
    if (!deal) return "—";
    return companies[deal.company_id] || "—";
  }

  return (
    <ProtectedShell>
      <h1 className="page-title">Dokumenty</h1>
      <p className="page-subtitle">Nabídky, objednávky, faktury a dodací listy napříč všemi případy</p>

      <div style={{ marginBottom: 18 }}>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          style={{ padding: "6px 10px", fontSize: 13, borderRadius: 6, border: "1px solid var(--line)" }}
        >
          <option value="">Všechny typy</option>
          {DOCUMENT_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="empty-state">Načítám…</div>
      ) : documents.length === 0 ? (
        <div className="empty-state">Žádné dokumenty neodpovídají filtru.</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Typ</th>
              <th>Firma</th>
              <th>Obchodní případ</th>
              <th>Vytvořeno</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => {
              const deal = deals[doc.deal_id];
              return (
                <tr key={doc.id}>
                  <td style={{ fontWeight: 600 }}>
                    {doc.document_type} {doc.version > 1 ? `(v${doc.version})` : ""}
                  </td>
                  <td>
                    {deals[doc.deal_id] ? (
                      <a href={`/companies/${deals[doc.deal_id].company_id}`} style={{ textDecoration: "underline" }}>
                        {companyNameForDeal(doc.deal_id)}
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>
                    {deal ? (
                      <a href={`/deals/${doc.deal_id}`} style={{ textDecoration: "underline" }}>
                        {deal.name}
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td style={{ color: "var(--ink-600)" }}>{formatDate(doc.created_at)}</td>
                  <td>
                    {doc.document_type === "Nabídka" && (
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
              );
            })}
          </tbody>
        </table>
      )}
    </ProtectedShell>
  );
}
