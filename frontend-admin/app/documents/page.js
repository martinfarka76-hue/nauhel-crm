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
        companiesData.forEach((c) => (companiesMap[c.id] = c));
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

  function companyForDeal(dealId) {
    const deal = deals[dealId];
    if (!deal) return null;
    return companies[deal.company_id] || null;
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
              const company = companyForDeal(doc.deal_id);
              return (
                <tr key={doc.id}>
                  <td style={{ fontWeight: 600 }}>
                    {doc.document_type} {doc.version > 1 ? `(v${doc.version})` : ""}
                  </td>
                  <td>
                    {company ? (
                      <a
                        href={`/companies/${company.id}`}
                        style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "underline" }}
                      >
                        <CompanyAvatar name={company.name} website={company.website} />
                        {company.name}
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
