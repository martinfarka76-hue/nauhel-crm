"use client";

import { useEffect, useState } from "react";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";
import { DEAL_STATUSES, STATUS_COLORS } from "@/lib/constants";

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

  function columnTotals(statusDeals, status) {
    const probability = (stageProbabilities[status] ?? 0) / 100;
    let total = 0;
    let weighted = 0;
    statusDeals.forEach((d) => {
      const price = Number(d.price) || 0;
      total += price;
      weighted += price * probability;
    });
    return { total, weighted };
  }

  return (
    <ProtectedShell>
      <h1 className="page-title">Přehled obchodních případů</h1>
      <p className="page-subtitle">Pipeline podle aktuálního stavu</p>

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
          onChange={(e) => setDateFrom(e.target.value)}
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
          onChange={(e) => setDateTo(e.target.value)}
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
          onChange={(e) => setInvoiceDateFrom(e.target.value)}
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
          onChange={(e) => setInvoiceDateTo(e.target.value)}
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
      </div>

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="empty-state">Načítám…</div>}

      {!loading && (
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
    </ProtectedShell>
  );
}
