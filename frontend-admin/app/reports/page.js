"use client";

import { useEffect, useState } from "react";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";

const MONTH_NAMES = ["Led", "Úno", "Bře", "Dub", "Kvě", "Čer", "Čvc", "Srp", "Zář", "Říj", "Lis", "Pro"];

const ACTIVE_STATUSES = [
  "Lead",
  "Kvalifikovaný lead",
  "Nabídka",
  "Objednávka",
  "Zálohová faktura",
  "Vyrobeno",
];

const DEFAULT_ORDER = ["new_deals", "invoice_forecast", "close_forecast", "win_rate", "product_line", "invoiced_history"];
const ORDER_STORAGE_KEY = "nauhel_reports_order";
const RANGE_OPTIONS = [3, 6, 12, 24];

// Konzistentní barevný systém - jedna barva (ember) pro objemové/finanční grafy
// v čase, zelená (--success) pro grafy "úspěch/realizováno", a kategorická
// paleta jen pro rozpad podle produktové řady (kde barva rozlišuje kategorie).
const CHART_COLOR_VOLUME = "var(--ember-500)";
const CHART_COLOR_SUCCESS = "var(--success)";
const PRODUCT_LINE_COLORS = {
  Atacama: "var(--ember-500)",
  Mirage: "#9c7c4f",
  Ocaso: "#5c564a",
};
const DEFAULT_PRODUCT_COLOR = "#c9c3b5";

function buildMonthRange(startOffset, endOffset) {
  const now = new Date();
  const result = [];
  for (let i = startOffset; i <= endOffset; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
    const year = d.getFullYear();
    const month = d.getMonth();
    const key = `${year}-${String(month + 1).padStart(2, "0")}`;
    const label = `${MONTH_NAMES[month]} ${String(year).slice(2)}`;
    result.push({ key, label, isCurrent: i === 0 });
  }
  return result;
}

function computeMonthlyData(deals, dateField, monthRange, { weighted = false, statusFilter = null, probabilities = {} } = {}) {
  const buckets = {};
  monthRange.forEach((m) => (buckets[m.key] = 0));

  deals.forEach((d) => {
    const dateVal = d[dateField];
    if (!dateVal) return;
    if (statusFilter && !statusFilter.includes(d.status)) return;
    const key = dateVal.slice(0, 7);
    if (!(key in buckets)) return;
    const price = Number(d.price) || 0;
    const value = weighted ? price * ((probabilities[d.status] ?? 0) / 100) : price;
    buckets[key] += value;
  });

  return monthRange.map((m) => ({ key: m.key, label: m.label, value: buckets[m.key], isCurrent: m.isCurrent }));
}

function computeWinRateData(deals, monthRange) {
  const buckets = {};
  monthRange.forEach((m) => (buckets[m.key] = { won: 0, lost: 0 }));

  deals.forEach((d) => {
    if (d.status !== "Fakturováno" && d.status !== "Ztraceno") return;
    const dateVal = d.expected_close_date;
    if (!dateVal) return;
    const key = dateVal.slice(0, 7);
    if (!(key in buckets)) return;
    if (d.status === "Fakturováno") buckets[key].won += 1;
    else buckets[key].lost += 1;
  });

  return monthRange.map((m) => {
    const { won, lost } = buckets[m.key];
    const total = won + lost;
    return {
      key: m.key,
      label: m.label,
      value: total > 0 ? (won / total) * 100 : 0,
      hasData: total > 0,
      isCurrent: m.isCurrent,
    };
  });
}

function computeProductLineData(deals, dealProductLine, probabilities, weighted) {
  const totals = {};
  deals.forEach((d) => {
    if (!ACTIVE_STATUSES.includes(d.status)) return;
    const line = dealProductLine[d.id] || "Nezadáno";
    const price = Number(d.price) || 0;
    const value = weighted ? price * ((probabilities[d.status] ?? 0) / 100) : price;
    totals[line] = (totals[line] || 0) + value;
  });
  return Object.entries(totals)
    .sort((a, b) => b[1] - a[1])
    .map(([label, value]) => ({
      key: label,
      label,
      value,
      isCurrent: false,
      color: PRODUCT_LINE_COLORS[label] || DEFAULT_PRODUCT_COLOR,
    }));
}

function formatKc(value) {
  if (value >= 1_000_000) return (value / 1_000_000).toFixed(1).replace(".", ",") + " M Kč";
  if (value >= 1000) return Math.round(value / 1000) + " tis. Kč";
  if (value === 0) return "";
  return Math.round(value) + " Kč";
}

function formatPercentValue(value, item) {
  if (item && item.hasData === false) return "";
  return Math.round(value) + " %";
}

function DragHandle() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
      <circle cx="8" cy="6" r="1.6" />
      <circle cx="16" cy="6" r="1.6" />
      <circle cx="8" cy="12" r="1.6" />
      <circle cx="16" cy="12" r="1.6" />
      <circle cx="8" cy="18" r="1.6" />
      <circle cx="16" cy="18" r="1.6" />
    </svg>
  );
}

function KpiCard({ label, value, color }) {
  return (
    <div className="card" style={{ flex: 1, textAlign: "center", padding: "16px 12px" }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: color || "var(--ink-900)" }}>{value}</div>
      <div style={{ fontSize: 12, color: "var(--ink-600)", marginTop: 4 }}>{label}</div>
    </div>
  );
}

function BarChart({
  id,
  title,
  description,
  data,
  color,
  formatValue = formatKc,
  fixedMax = null,
  summaryLabel = null,
  summaryValue = null,
  onDragStartCard,
  onDragOverCard,
  onDropCard,
  isDragging,
}) {
  const maxValue = fixedMax ?? Math.max(...data.map((d) => d.value), 1);
  const total = summaryValue !== null ? summaryValue : data.reduce((sum, d) => sum + d.value, 0);
  const gridLines = [0, 0.33, 0.66, 1];

  return (
    <div
      className="card"
      draggable
      onDragStart={() => onDragStartCard(id)}
      onDragOver={(e) => {
        e.preventDefault();
        onDragOverCard(id);
      }}
      onDrop={() => onDropCard(id)}
      style={{
        marginBottom: 20,
        opacity: isDragging ? 0.4 : 1,
        cursor: "grab",
        border: isDragging ? "1px dashed var(--ember-500)" : undefined,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ color: "var(--ink-400)" }}>
            <DragHandle />
          </span>
          <div style={{ fontWeight: 600 }}>{title}</div>
        </div>
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--ember-600)" }}>
          {summaryLabel ? `${summaryLabel}: ` : ""}
          {formatValue(total) || "0"}
        </div>
      </div>
      {description && (
        <div style={{ fontSize: 12, color: "var(--ink-600)", marginBottom: 16, paddingLeft: 22 }}>{description}</div>
      )}
      <div style={{ position: "relative", height: 180 }}>
        {gridLines.map((g) => (
          <div
            key={g}
            style={{ position: "absolute", left: 0, right: 0, bottom: `${g * 100}%`, borderTop: "1px solid var(--paper-200)" }}
          />
        ))}
        <div style={{ position: "relative", display: "flex", alignItems: "flex-end", gap: 6, height: "100%" }}>
          {data.map((d) => (
            <div
              key={d.key}
              style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", height: "100%", justifyContent: "flex-end" }}
            >
              <div style={{ fontSize: 10.5, color: "var(--ink-600)", marginBottom: 4, whiteSpace: "nowrap" }}>
                {formatValue(d.value, d)}
              </div>
              <div
                title={`${d.label}: ${formatValue(d.value, d)}`}
                style={{
                  width: "100%",
                  height: `${d.value > 0 ? Math.max((d.value / maxValue) * 100, 3) : 0}%`,
                  background: d.color || color,
                  opacity: d.isCurrent ? 1 : 0.75,
                  borderRadius: "4px 4px 0 0",
                  minHeight: d.value > 0 ? 3 : 0,
                }}
              />
            </div>
          ))}
        </div>
      </div>
      <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
        {data.map((d) => (
          <div
            key={d.key}
            style={{
              flex: 1,
              textAlign: "center",
              fontSize: 11,
              color: d.isCurrent ? "var(--ink-900)" : "var(--ink-400)",
              fontWeight: d.isCurrent ? 700 : 400,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {d.label}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ReportsPage() {
  const [deals, setDeals] = useState([]);
  const [users, setUsers] = useState([]);
  const [probabilities, setProbabilities] = useState({});
  const [dealProductLine, setDealProductLine] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [order, setOrder] = useState(DEFAULT_ORDER);
  const [draggedId, setDraggedId] = useState(null);
  const [dragOverId, setDragOverId] = useState(null);
  const [volumeMode, setVolumeMode] = useState("weighted");
  const [ownerFilter, setOwnerFilter] = useState("");
  const [rangeMonths, setRangeMonths] = useState(12);

  useEffect(() => {
    Promise.all([api.get("/deals"), api.get("/stage-config"), api.get("/users")])
      .then(([dealsData, stageConfig, usersData]) => {
        setDeals(dealsData);
        setUsers(usersData);
        const probMap = {};
        stageConfig.forEach((s) => (probMap[s.stage_name] = s.probability_percent));
        setProbabilities(probMap);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));

    const savedOrder = window.localStorage.getItem(ORDER_STORAGE_KEY);
    if (savedOrder) {
      try {
        const parsed = JSON.parse(savedOrder);
        if (Array.isArray(parsed) && parsed.length === DEFAULT_ORDER.length) {
          setOrder(parsed);
        }
      } catch {
        // ignorovat poškozená data
      }
    }
  }, []);

  useEffect(() => {
    if (deals.length === 0) return;
    const activeDeals = deals.filter((d) => ACTIVE_STATUSES.includes(d.status));
    Promise.all(
      activeDeals.map((d) =>
        api
          .get(`/deals/${d.id}/calculations`)
          .then((calcs) => {
            const activeCalc = calcs.find((c) => c.is_active);
            return { dealId: d.id, productLine: activeCalc?.product_line || null };
          })
          .catch(() => ({ dealId: d.id, productLine: null }))
      )
    ).then((results) => {
      const map = {};
      results.forEach((r) => (map[r.dealId] = r.productLine));
      setDealProductLine(map);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deals]);

  function persistOrder(newOrder) {
    setOrder(newOrder);
    window.localStorage.setItem(ORDER_STORAGE_KEY, JSON.stringify(newOrder));
  }

  function handleDrop(targetId) {
    if (!draggedId || draggedId === targetId) {
      setDraggedId(null);
      setDragOverId(null);
      return;
    }
    const newOrder = [...order];
    const fromIdx = newOrder.indexOf(draggedId);
    const toIdx = newOrder.indexOf(targetId);
    newOrder.splice(fromIdx, 1);
    newOrder.splice(toIdx, 0, draggedId);
    persistOrder(newOrder);
    setDraggedId(null);
    setDragOverId(null);
  }

  if (loading) {
    return (
      <ProtectedShell>
        <div className="empty-state">Načítám…</div>
      </ProtectedShell>
    );
  }

  const filteredDeals = ownerFilter ? deals.filter((d) => d.owner_user_id === ownerFilter) : deals;

  const historyRange = buildMonthRange(-(rangeMonths - 1), 0);
  const forecastRange = buildMonthRange(0, rangeMonths - 1);
  const isWeighted = volumeMode === "weighted";

  // --- KPI výpočty ---
  const activeDealsFiltered = filteredDeals.filter((d) => ACTIVE_STATUSES.includes(d.status));
  const pipelineWeighted = activeDealsFiltered.reduce(
    (sum, d) => sum + (Number(d.price) || 0) * ((probabilities[d.status] ?? 0) / 100),
    0
  );
  const nonLostDeals = filteredDeals.filter((d) => d.status !== "Ztraceno");
  const avgDealValue = nonLostDeals.length > 0
    ? nonLostDeals.reduce((sum, d) => sum + (Number(d.price) || 0), 0) / nonLostDeals.length
    : 0;
  const wonCount = filteredDeals.filter((d) => d.status === "Fakturováno").length;
  const lostCount = filteredDeals.filter((d) => d.status === "Ztraceno").length;
  const winRateOverall = wonCount + lostCount > 0 ? (wonCount / (wonCount + lostCount)) * 100 : null;

  const charts = {
    new_deals: {
      title: "Nové obchodní případy podle měsíce",
      description: `Objem (cena) nově vytvořených případů - posledních ${rangeMonths} měsíců, podle data vzniku`,
      data: computeMonthlyData(filteredDeals, "created_at", historyRange),
      color: CHART_COLOR_VOLUME,
    },
    invoice_forecast: {
      title: `Výhled fakturací podle měsíce (${isWeighted ? "vážený objem" : "celkem"})`,
      description: `Odhadovaná fakturace u aktivních případů${isWeighted ? ", vážená pravděpodobností stavu" : ""} - příštích ${rangeMonths} měsíců`,
      data: computeMonthlyData(filteredDeals, "expected_invoice_date", forecastRange, {
        weighted: isWeighted,
        statusFilter: ACTIVE_STATUSES,
        probabilities,
      }),
      color: CHART_COLOR_VOLUME,
    },
    close_forecast: {
      title: `Výhled uzavření podle měsíce (${isWeighted ? "vážený objem" : "celkem"})`,
      description: `Odhadované uzavření u aktivních případů${isWeighted ? ", vážené pravděpodobností stavu" : ""} - příštích ${rangeMonths} měsíců`,
      data: computeMonthlyData(filteredDeals, "expected_close_date", forecastRange, {
        weighted: isWeighted,
        statusFilter: ACTIVE_STATUSES,
        probabilities,
      }),
      color: CHART_COLOR_VOLUME,
    },
    win_rate: {
      title: "Míra úspěšnosti podle měsíce",
      description: "Podíl Fakturováno vs. Ztraceno (podle odhadovaného data uzavření) - jen měsíce s rozhodnutým výsledkem",
      data: computeWinRateData(filteredDeals, historyRange),
      color: CHART_COLOR_SUCCESS,
      formatValue: formatPercentValue,
      fixedMax: 100,
      summaryLabel: "Průměr",
      summaryValue: (() => {
        const wr = computeWinRateData(filteredDeals, historyRange).filter((d) => d.hasData);
        return wr.length > 0 ? wr.reduce((s, d) => s + d.value, 0) / wr.length : 0;
      })(),
    },
    product_line: {
      title: `Rozpad podle produktové řady (${isWeighted ? "vážený objem" : "celkem"})`,
      description: "Aktivní případy podle produktové řady vybrané v kalkulaci",
      data: computeProductLineData(filteredDeals, dealProductLine, probabilities, isWeighted),
      color: CHART_COLOR_VOLUME,
    },
    invoiced_history: {
      title: "Historie fakturovaného objemu",
      description: `Skutečně fakturované případy podle odhadovaného data fakturace - posledních ${rangeMonths} měsíců`,
      data: computeMonthlyData(filteredDeals, "expected_invoice_date", historyRange, {
        statusFilter: ["Fakturováno"],
      }),
      color: CHART_COLOR_SUCCESS,
    },
  };

  return (
    <ProtectedShell>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 className="page-title">Reporty</h1>
          <p className="page-subtitle">Plánování obchodů a fakturací - historie i výhled dopředu</p>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={ownerFilter}
            onChange={(e) => setOwnerFilter(e.target.value)}
            style={{ padding: "7px 10px", fontSize: 13, borderRadius: 8, border: "1px solid var(--paper-200)" }}
          >
            <option value="">Všichni vlastníci</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name}
              </option>
            ))}
          </select>
          <select
            value={rangeMonths}
            onChange={(e) => setRangeMonths(Number(e.target.value))}
            style={{ padding: "7px 10px", fontSize: 13, borderRadius: 8, border: "1px solid var(--paper-200)" }}
          >
            {RANGE_OPTIONS.map((m) => (
              <option key={m} value={m}>
                {m} měsíců
              </option>
            ))}
          </select>
          <div style={{ display: "flex", gap: 2, background: "var(--paper-200)", borderRadius: 8, padding: 2 }}>
            <button
              onClick={() => setVolumeMode("weighted")}
              style={{
                border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 13, cursor: "pointer",
                background: isWeighted ? "#fff" : "transparent", fontWeight: isWeighted ? 600 : 400,
                color: isWeighted ? "var(--ink-900)" : "var(--ink-600)",
              }}
            >
              Vážený objem
            </button>
            <button
              onClick={() => setVolumeMode("total")}
              style={{
                border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 13, cursor: "pointer",
                background: !isWeighted ? "#fff" : "transparent", fontWeight: !isWeighted ? 600 : 400,
                color: !isWeighted ? "var(--ink-900)" : "var(--ink-600)",
              }}
            >
              Celkem
            </button>
          </div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 12, margin: "20px 0" }}>
        <KpiCard label="Vážený objem v pipeline" value={formatKc(pipelineWeighted) || "0 Kč"} color="var(--ember-600)" />
        <KpiCard label="Aktivních případů" value={activeDealsFiltered.length} />
        <KpiCard label="Průměrná hodnota zakázky" value={formatKc(avgDealValue) || "0 Kč"} />
        <KpiCard
          label="Míra úspěšnosti"
          value={winRateOverall !== null ? `${Math.round(winRateOverall)} %` : "—"}
          color={winRateOverall !== null ? "var(--success)" : undefined}
        />
      </div>

      <div style={{ fontSize: 11.5, color: "var(--ink-400)", marginBottom: 16 }}>
        Přepínač objemu platí pro výhledové a produktové grafy. Karty grafů jde přetáhnout myší a přeuspořádat.
      </div>

      {error && <div className="error-banner">{error}</div>}

      {order.map((chartId) => (
        <BarChart
          key={chartId}
          id={chartId}
          {...charts[chartId]}
          onDragStartCard={setDraggedId}
          onDragOverCard={setDragOverId}
          onDropCard={handleDrop}
          isDragging={draggedId === chartId}
        />
      ))}
    </ProtectedShell>
  );
}
