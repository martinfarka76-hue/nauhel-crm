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

export default function DashboardPage() {
  const [deals, setDeals] = useState([]);
  const [companies, setCompanies] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.get("/deals"), api.get("/companies")])
      .then(([dealsData, companiesData]) => {
        setDeals(dealsData);
        const map = {};
        companiesData.forEach((c) => (map[c.id] = c.name));
        setCompanies(map);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const dealsByStatus = {};
  DEAL_STATUSES.forEach((s) => (dealsByStatus[s] = []));
  deals.forEach((d) => {
    if (dealsByStatus[d.status]) dealsByStatus[d.status].push(d);
  });

  return (
    <ProtectedShell>
      <h1 className="page-title">Přehled obchodních případů</h1>
      <p className="page-subtitle">Pipeline podle aktuálního stavu</p>

      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="empty-state">Načítám…</div>}

      {!loading && (
        <div className="kanban">
          {DEAL_STATUSES.map((status) => (
            <div className="kanban-col" key={status}>
              <div className="kanban-col-header">
                <span
                  className="kanban-col-dot"
                  style={{ background: STATUS_COLORS[status] }}
                />
                <span className="kanban-col-title">{status}</span>
                <span className="kanban-col-count">{dealsByStatus[status].length}</span>
              </div>
              <div className="kanban-cards">
                {dealsByStatus[status].map((deal) => (
                  <a
                    key={deal.id}
                    href={`/deals/${deal.id}`}
                    className="deal-card"
                    style={{ borderLeftColor: STATUS_COLORS[status], display: "block" }}
                  >
                    <div className="deal-card-name">{deal.name}</div>
                    <div className="deal-card-company">
                      {companies[deal.company_id] || "—"}
                    </div>
                    <div className="deal-card-price mono">{formatPrice(deal.price)}</div>
                  </a>
                ))}
                {dealsByStatus[status].length === 0 && (
                  <div style={{ fontSize: 12, color: "var(--ink-400)", padding: "8px 2px" }}>
                    Žádné případy
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </ProtectedShell>
  );
}
