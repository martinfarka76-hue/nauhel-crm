"use client";

import { useEffect, useState } from "react";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";
import { DEAL_STATUSES, STATUS_COLORS } from "@/lib/constants";

const PAGE_SIZE = 50;

function formatPrice(price) {
  if (price === null || price === undefined) return "—";
  const n = Math.round(Number(price));
  return n.toLocaleString("cs-CZ") + " Kč";
}

function formatDateShort(dateStr) {
  if (!dateStr) return null;
  const [y, m, d] = dateStr.split("-");
  return `${d}.${m}.${y}`;
}

function csvEscape(value) {
  const str = String(value ?? "");
  if (str.includes(";") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
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

const emptyNewDealForm = {
  company_id: "",
  contact_id: "",
  owner_user_id: "",
  name: "",
  price: "",
  expected_close_date: "",
  expected_invoice_date: "",
};

export default function DashboardPage() {
  const [deals, setDeals] = useState([]);
  const [companiesList, setCompaniesList] = useState([]);
  const [companies, setCompanies] = useState({});
  const [companyWebsites, setCompanyWebsites] = useState({});
  const [users, setUsers] = useState([]);
  const [usersById, setUsersById] = useState({});
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

  const [showNewDealForm, setShowNewDealForm] = useState(false);
  const [newDealForm, setNewDealForm] = useState(emptyNewDealForm);
  const [newDealContacts, setNewDealContacts] = useState([]);
  const [savingNewDeal, setSavingNewDeal] = useState(false);

  function loadAll() {
    setLoading(true);
    Promise.all([
      api.get("/deals"),
      api.get("/companies"),
      api.get("/stage-config"),
      api.get("/users"),
      api.get("/auth/me"),
    ])
      .then(([dealsData, companiesData, stageConfigData, usersData, me]) => {
        setDeals(dealsData);
        setCompaniesList(companiesData);
        const map = {};
        const websiteMap = {};
        companiesData.forEach((c) => {
          map[c.id] = c.name;
          websiteMap[c.id] = c.website;
        });
        setCompanies(map);
        setCompanyWebsites(websiteMap);
        const probMap = {};
        stageConfigData.forEach((s) => (probMap[s.stage_name] = s.probability_percent));
        setStageProbabilities(probMap);
        setUsers(usersData);
        const usersMap = {};
        usersData.forEach((u) => (usersMap[u.id] = u.full_name));
        setUsersById(usersMap);
        setNewDealForm((prev) => ({ ...prev, owner_user_id: prev.owner_user_id || me.id }));
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(loadAll, []);

  useEffect(() => {
    if (!newDealForm.company_id) {
      setNewDealContacts([]);
      return;
    }
    api
      .get(`/contacts?company_id=${newDealForm.company_id}`)
      .then(setNewDealContacts)
      .catch(() => setNewDealContacts([]));
  }, [newDealForm.company_id]);

  async function handleCreateDeal(e) {
    e.preventDefault();
    setSavingNewDeal(true);
    setError("");
    try {
      await api.post("/deals", {
        company_id: newDealForm.company_id,
        contact_id: newDealForm.contact_id || null,
        owner_user_id: newDealForm.owner_user_id || null,
        name: newDealForm.name,
        status: "Lead",
        price: newDealForm.price ? Number(newDealForm.price) : null,
        expected_close_date: newDealForm.expected_close_date || null,
        expected_invoice_date: newDealForm.expected_invoice_date || null,
      });
      setNewDealForm({ ...emptyNewDealForm, owner_user_id: newDealForm.owner_user_id });
      setShowNewDealForm(false);
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingNewDeal(false);
    }
  }

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
    if (key === "owner") return usersById[deal.owner_user_id] || "";
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
    const header = ["Název", "Firma", "Stav", "Cena", "Vlastník", "Uzavření", "Fakturace"];
    const rows = sortedDeals.map((d) => [
      d.name,
      companies[d.company_id] || "",
      d.status,
      d.price ?? "",
      usersById[d.owner_user_id] || "",
      d.expected_close_date || "",
      d.expected_invoice_date || "",
    ]);
    const csvLines = [header, ...rows].map((row) => row.map(csvEscape).join(";"));
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
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          rowGap: 10,
          marginBottom: 16,
        }}
      >
        <h1 className="page-title" style={{ margin: 0 }}>
          Přehled obchodních případů
        </h1>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <button className="btn btn-primary" onClick={() => setShowNewDealForm(!showNewDealForm)}>
            {showNewDealForm ? "Zrušit" : "+ Nový obchodní případ"}
          </button>
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
      </div>

      {showNewDealForm && (
        <div className="card" style={{ marginBottom: 20, maxWidth: 560 }}>
          <form onSubmit={handleCreateDeal}>
            <div className="field">
              <label>Firma *</label>
              <select
                required
                value={newDealForm.company_id}
                onChange={(e) =>
                  setNewDealForm({ ...newDealForm, company_id: e.target.value, contact_id: "" })
                }
              >
                <option value="">— vyber firmu —</option>
                {companiesList.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Odpovědný kontakt</label>
              <select
                value={newDealForm.contact_id}
                onChange={(e) => setNewDealForm({ ...newDealForm, contact_id: e.target.value })}
                disabled={!newDealForm.company_id}
              >
                <option value="">— žádný / nevybráno —</option>
                {newDealContacts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.first_name} {c.last_name} {c.position ? `(${c.position})` : ""}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Vlastník případu (obchodník)</label>
              <select
                value={newDealForm.owner_user_id}
                onChange={(e) => setNewDealForm({ ...newDealForm, owner_user_id: e.target.value })}
              >
                <option value="">— nepřiřazeno —</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Název případu *</label>
              <input
                required
                value={newDealForm.name}
                onChange={(e) => setNewDealForm({ ...newDealForm, name: e.target.value })}
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>Odhad. cena (Kč)</label>
                <input
                  type="number"
                  value={newDealForm.price}
                  onChange={(e) => setNewDealForm({ ...newDealForm, price: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Odhad. uzavření</label>
                <input
                  type="date"
                  value={newDealForm.expected_close_date}
                  onChange={(e) => setNewDealForm({ ...newDealForm, expected_close_date: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Odhad. fakturace</label>
                <input
                  type="date"
                  value={newDealForm.expected_invoice_date}
                  onChange={(e) => setNewDealForm({ ...newDealForm, expected_invoice_date: e.target.value })}
                />
              </div>
            </div>
            <button className="btn btn-primary" type="submit" disabled={savingNewDeal}>
              {savingNewDeal ? "Vytvářím…" : "Vytvořit případ"}
            </button>
          </form>
        </div>
      )}

      <div
        style={{
          display: "flex",
          gap: 14,
          alignItems: "center",
          marginBottom: 16,
          padding: "9px 14px",
          background: "var(--paper-50)",
          border: "1px solid var(--paper-200)",
          borderRadius: 10,
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
                  {statusDeals.map((deal) => {
                    const companyName = companies[deal.company_id] || "—";
                    const initial = companyName !== "—" ? companyName.charAt(0).toUpperCase() : "?";
                    const domain = getDomain(companyWebsites[deal.company_id]);
                    return (
                      <a
                        key={deal.id}
                        href={`/deals/${deal.id}`}
                        className="deal-card"
                        style={{ borderLeftColor: STATUS_COLORS[status], display: "block" }}
                      >
                        <div className="deal-card-top">
                          {domain ? (
                            <>
                              <img
                                src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`}
                                alt=""
                                className="deal-card-avatar-img"
                                onError={(e) => {
                                  e.target.style.display = "none";
                                  e.target.nextElementSibling.style.display = "flex";
                                }}
                              />
                              <span className="deal-card-avatar" style={{ display: "none" }}>
                                {initial}
                              </span>
                            </>
                          ) : (
                            <span className="deal-card-avatar">{initial}</span>
                          )}
                          <span className="deal-card-company">{companyName}</span>
                        </div>
                        <div className="deal-card-name">{deal.name}</div>
                        <div className="deal-card-price mono">{formatPrice(deal.price)}</div>

                        {(deal.expected_close_date || deal.expected_invoice_date || deal.owner_user_id) && (
                          <div className="deal-card-meta">
                            {deal.expected_close_date && (
                              <div className="deal-card-meta-row">
                                <span className="deal-card-meta-label">Uzavření</span>
                                <span>{formatDateShort(deal.expected_close_date)}</span>
                              </div>
                            )}
                            {deal.expected_invoice_date && (
                              <div className="deal-card-meta-row">
                                <span className="deal-card-meta-label">Fakturace</span>
                                <span>{formatDateShort(deal.expected_invoice_date)}</span>
                              </div>
                            )}
                            {deal.owner_user_id && usersById[deal.owner_user_id] && (
                              <div className="deal-card-meta-row">
                                <span className="deal-card-meta-label">Vlastník</span>
                                <span style={{ color: "var(--ember-600)", fontWeight: 600 }}>
                                  {usersById[deal.owner_user_id]}
                                </span>
                              </div>
                            )}
                          </div>
                        )}
                      </a>
                    );
                  })}
                  {statusDeals.length === 0 && (
                    <div style={{ fontSize: 12, color: "var(--ink-400)", padding: "8px 2px" }}>Žádné případy</div>
                  )}
                </div>
                {statusDeals.length > 0 && (
                  <div className="kanban-col-totals">
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
                    <SortHeader label="Vlastník" sortKeyName="owner" />
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
                      <td>{usersById[deal.owner_user_id] || "—"}</td>
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
