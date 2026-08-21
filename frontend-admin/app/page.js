"use client";

import { useEffect, useState } from "react";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";
import { DEAL_STATUSES, STATUS_COLORS } from "@/lib/constants";

const PAGE_SIZE = 50;

function formatPrice(price) {
  if (price === null || price === undefined) return "—";
  const n = Number(price);
  return n.toLocaleString("cs-CZ") + " Kč";
}

function formatDateShort(dateStr) {
  if (!dateStr) return null;
  const [y, m, d] = dateStr.split("-");
  return `${d}.${m}.`;
}

function csvEscape(value) {
  const str = String(value ?? "");
  if (str.includes(";") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export default function DashboardPage() {
  const [deals, setDeals] = useState([]);
  const [companies, setCompanies] = useState({});
  const [stageProbabilities, setStageProbabilities] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [invoiceDateFrom, setInvoiceDateFrom] = useState("");
  const [invoiceDateTo, setInvoiceDateTo] = useState("");

  const [viewMode, setViewMode] = useState("kanban"); // "kanban" | "list"
  const [sortKey, setSortKey] = useState("created_at");
  const [sortDir, setSortDir] = useState("desc"); // "asc" | "desc"
  const [page, setPage] = useState(1);

  useEffect(() => {
    Promise.all([api.get("/deals"), api.get("/companies"), api.get("/stage-config")])
      .then(([dealsData, companiesData, stageConfigData]) => {
        setDeals(dealsData);
        const map = {};
        companiesData.forEach((c) => (map[c.id] = c.name));
        setCompanies(map);
        const probMap = {};
        stageConfigData.forEach((s) => (probMap[s.stage_name] = s.probability_percent));
        setStageProbabilities(probMap);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const hasDateFilter = !!(dateFrom || dateTo || invoiceDateFrom || invoiceDateTo);

  function matchesDateFilter(deal) {
    if (dateFrom || dateTo) {
      if (!deal.expected_close_date) return false;
      if (dateFrom && deal.expected_close_date < dateFrom) return false;
      if (dateTo && deal.expected_close_date > dateTo) return false;
    }
    if (invoiceDateFrom || invoiceDateTo) {
      if (!deal.expected_invoice_date) return false;
      if (invoiceDateFrom && deal.expected_invoice_date < invoiceDateFrom) return false;
      if (invoiceDateTo && deal.expected_invoice_date > invoiceDateTo) return false;
    }
    return true;
  }

  const filteredDeals = deals.filter(matchesDateFilter);

  const dealsByStatus = {};
  DEAL_STATUSES.forEach((s) => (dealsByStatus[s] = []));
  filteredDeals.forEach((d) => {
    if (dealsByStatus[d.status]) dealsByStatus[d.status].push(d);
  });

  function probabilityFor(status) {
    return (stageProbabilities[status] ?? 0) / 100;
  }

  function columnTotals(statusDeals, status) {
    const probability = probabilityFor(status);
    let total = 0;
    let weighted = 0;
    statusDeals.forEach((d) => {
      const price = Number(d.price) || 0;
      total += price;
      weighted += price * probability;
    });
    return { total, weighted };
  }

  // Celkové součty přes všechny filtrované případy (napříč stavy) - pro seznam
  const overallTotals = filteredDeals.reduce(
    (acc, d) => {
      const price = Number(d.price) || 0;
      acc.total += price;
      acc.weighted += price * probabilityFor(d.status);
      return acc;
    },
    { total: 0, weighted: 0 }
  );

  function handleSort(key) {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
    setPage(1);
  }

  function sortValue(deal, key) {
    if (key === "company") return companies[deal.company_id] || "";
    if (key === "price") return Number(deal.price) || 0;
    return deal[key] || "";
  }

  const sortedDeals = [...filteredDeals].sort((a, b) => {
    const va = sortValue(a, sortKey);
    const vb = sortValue(b, sortKey);
    if (va < vb) return sortDir === "asc" ? -1 : 1;
    if (va > vb) return sortDir === "asc" ? 1 : -1;
    return 0;
  });

  const totalPages = Math.max(1, Math.ceil(sortedDeals.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedDeals = sortedDeals.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  function SortHeader({ label, sortKeyName }) {
    const active = sortKey === sortKeyName;
    return (
      <th
        onClick={() => handleSort(sortKeyName)}
        style={{ cursor: "pointer", userSelect: "none", color: active ? "var(--ink-900)" : undefined }}
      >
        {label} {active && (sortDir === "asc" ? "↑" : "↓")}
      </th>
    );
  }

  function handleExportCsv() {
    const header = ["Název", "Firma", "Stav", "Cena", "Uzavření", "Fakturace"];
    const rows = sortedDeals.map((d) => [
      d.name,
      companies[d.company_id] || "",
      d.status,
      d.price ?? "",
      d.expected_close_date || "",
      d.expected_invoice_date || "",
    ]);
    const csvLines = [header, ...rows].map((row) => row.map(csvEscape).join(";"));
    // BOM na začátku, ať Excel správně rozpozná UTF-8 (jinak by zobrazoval diakritiku špatně)
    const csvContent = "\uFEFF" + csvLines.join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `obchodni-pripady-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <ProtectedShell>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", maxWidth: 720 }}>
        <div>
          <h1 className="page-title">Přehled obchodních případů</h1>
          <p className="page-subtitle">Pipeline podle aktuálního stavu</p>
        </div>
        <div style={{ display: "flex", gap: 2, background: "var(--paper-200)", borderRadius: 8, padding: 2 }}>
          <button
            onClick={() => setViewMode("kanban")}
            style={{
              border: "none",
              borderRadius: 6,
              padding: "6px 14px",
              fontSize: 13,
              cursor: "pointer",
              background: viewMode === "kanban" ? "#fff" : "transparent",
              fontWeight: viewMode === "kanban" ? 600 : 400,
              color: viewMode === "kanban" ? "var(--ink-900)" : "var(--ink-600)",
            }}
          >
            Mřížka
          </button>
          <button
            onClick={() => setViewMode("list")}
            style={{
              border: "none",
              borderRadius: 6,
              padding: "6px 14px",
              fontSize: 13,
              cursor: "pointer",
              background: viewMode === "list" ? "#fff" : "transparent",
              fontWeight: viewMode === "list" ? 600 : 400,
              color: viewMode === "list" ? "var(--ink-900)" : "var(--ink-600)",
            }}
          >
            Seznam
          </button>
        </div>
      </div>

      <div
        style={{
          display: "flex",
          gap: 14,
          alignItems: "center",
          marginBottom: 20,
          paddingBottom: 12,
          borderBottom: "1px solid var(--paper-200)",
          fontSize: 12.5,
        }}
      >
        <span style={{ color: "var(--ink-400)" }}>Uzavření</span>
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => {
            setDateFrom(e.target.value);
            setPage(1);
          }}
          style={{
            border: "1px solid var(--paper-200)",
            borderRadius: 5,
            padding: "3px 6px",
            fontSize: 12.5,
            color: "var(--ink-600)",
          }}
        />
        <span style={{ color: "var(--ink-400)" }}>–</span>
        <input
          type="date"
          value={dateTo}
          onChange={(e) => {
            setDateTo(e.target.value);
            setPage(1);
          }}
          style={{
            border: "1px solid var(--paper-200)",
            borderRadius: 5,
            padding: "3px 6px",
            fontSize: 12.5,
            color: "var(--ink-600)",
          }}
        />

        <span style={{ color: "var(--paper-200)" }}>|</span>

        <span style={{ color: "var(--ink-400)" }}>Fakturace</span>
        <input
          type="date"
          value={invoiceDateFrom}
          onChange={(e) => {
            setInvoiceDateFrom(e.target.value);
            setPage(1);
          }}
          style={{
            border: "1px solid var(--paper-200)",
            borderRadius: 5,
            padding: "3px 6px",
            fontSize: 12.5,
            color: "var(--ink-600)",
          }}
        />
        <span style={{ color: "var(--ink-400)" }}>–</span>
        <input
          type="date"
          value={invoiceDateTo}
          onChange={(e) => {
            setInvoiceDateTo(e.target.value);
            setPage(1);
          }}
          style={{
            border: "1px solid var(--paper-200)",
            borderRadius: 5,
            padding: "3px 6px",
            fontSize: 12.5,
            color: "var(--ink-600)",
          }}
        />

        {hasDateFilter && (
          <button
            onClick={() => {
              setDateFrom("");
              setDateTo("");
              setInvoiceDateFrom("");
              setInvoiceDateTo("");
              setPage(1);
            }}
            style={{
              background: "none",
              border: "none",
              color: "var(--ember-500)",
              fontSize: 12.5,
              cursor: "pointer",
              textDecoration: "underline",
              padding: 0,
            }}
          >
            Zrušit filtr
          </button>
        )}

        {viewMode === "list" && (
          <button
            onClick={handleExportCsv}
            style={{
              marginLeft: "auto",
              background: "none",
              border: "1px solid var(--line)",
              borderRadius: 6,
              padding: "4px 10px",
              fontSize: 12.5,
              color: "var(--ink-600)",
              cursor: "pointer",
            }}
          >
            Export do Excelu (CSV)
          </button>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="empty-state">Načítám…</div>}

      {!loading && viewMode === "kanban" && (
        <div className="kanban">
          {DEAL_STATUSES.map((status) => {
            const statusDeals = dealsByStatus[status];
            const { total, weighted } = columnTotals(statusDeals, status);
            return (
              <div className="kanban-col" key={status}>
                <div className="kanban-col-header">
                  <span className="kanban-col-dot" style={{ background: STATUS_COLORS[status] }} />
                  <span className="kanban-col-title">{status}</span>
                  <span className="kanban-col-count">{statusDeals.length}</span>
                </div>
                <div className="kanban-cards">
                  {statusDeals.map((deal) => (
                    <a
                      key={deal.id}
                      href={`/deals/${deal.id}`}
                      className="deal-card"
                      style={{ borderLeftColor: STATUS_COLORS[status], display: "block" }}
                    >
                      <div className="deal-card-name">{deal.name}</div>
                      <div className="deal-card-company">{companies[deal.company_id] || "—"}</div>
                      <div className="deal-card-price mono">{formatPrice(deal.price)}</div>
                      {(deal.expected_close_date || deal.expected_invoice_date) && (
                        <div style={{ fontSize: 11, color: "var(--ink-400)", marginTop: 4 }}>
                          {deal.expected_close_date && <span>Uzavření {formatDateShort(deal.expected_close_date)}</span>}
                          {deal.expected_close_date && deal.expected_invoice_date && <span> · </span>}
                          {deal.expected_invoice_date && <span>Fakturace {formatDateShort(deal.expected_invoice_date)}</span>}
                        </div>
                      )}
                    </a>
                  ))}
                  {statusDeals.length === 0 && (
                    <div style={{ fontSize: 12, color: "var(--ink-400)", padding: "8px 2px" }}>Žádné případy</div>
                  )}
                </div>
                {statusDeals.length > 0 && (
                  <div
                    style={{
                      marginTop: 10,
                      paddingTop: 8,
                      borderTop: "1px solid var(--paper-200)",
                      fontSize: 11.5,
                      color: "var(--ink-600)",
                    }}
                  >
                    <div>
                      Celkem: <strong className="mono">{formatPrice(total)}</strong>
                    </div>
                    <div>
                      Vážený objem: <strong className="mono">{formatPrice(weighted)}</strong>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!loading && viewMode === "list" && (
        <>
          {sortedDeals.length === 0 ? (
            <div className="empty-state">Žádné obchodní případy neodpovídají filtru.</div>
          ) : (
            <>
              <table className="table">
                <thead>
                  <tr>
                    <SortHeader label="Název" sortKeyName="name" />
                    <SortHeader label="Firma" sortKeyName="company" />
                    <SortHeader label="Stav" sortKeyName="status" />
                    <SortHeader label="Cena" sortKeyName="price" />
                    <SortHeader label="Uzavření" sortKeyName="expected_close_date" />
                    <SortHeader label="Fakturace" sortKeyName="expected_invoice_date" />
                  </tr>
                </thead>
                <tbody>
                  {pagedDeals.map((deal) => (
                    <tr key={deal.id} className="clickable" onClick={() => (window.location.href = `/deals/${deal.id}`)}>
                      <td style={{ fontWeight: 600 }}>{deal.name}</td>
                      <td>{companies[deal.company_id] || "—"}</td>
                      <td>
                        <span className="badge" style={{ background: STATUS_COLORS[deal.status] }}>
                          {deal.status}
                        </span>
                      </td>
                      <td className="mono">{formatPrice(deal.price)}</td>
                      <td className="mono">{formatDateShort(deal.expected_close_date) || "—"}</td>
                      <td className="mono">{formatDateShort(deal.expected_invoice_date) || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginTop: 16,
                  paddingTop: 12,
                  borderTop: "1px solid var(--paper-200)",
                }}
              >
                <div style={{ fontSize: 13, color: "var(--ink-600)" }}>
                  Celkem ({sortedDeals.length}): <strong className="mono">{formatPrice(overallTotals.total)}</strong>
                  {"  ·  "}
                  Vážený objem: <strong className="mono">{formatPrice(overallTotals.weighted)}</strong>
                </div>

                {totalPages > 1 && (
                  <div style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13 }}>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: "4px 10px", fontSize: 12.5 }}
                      disabled={currentPage <= 1}
                      onClick={() => setPage(currentPage - 1)}
                    >
                      Předchozí
                    </button>
                    <span style={{ color: "var(--ink-600)" }}>
                      Strana {currentPage} z {totalPages}
                    </span>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: "4px 10px", fontSize: 12.5 }}
                      disabled={currentPage >= totalPages}
                      onClick={() => setPage(currentPage + 1)}
                    >
                      Další
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </>
      )}
    </ProtectedShell>
  );
}
