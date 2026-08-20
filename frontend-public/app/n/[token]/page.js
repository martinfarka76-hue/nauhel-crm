"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { fetchPublicDocument, sendViewDuration } from "@/lib/api";

function formatMoney(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("cs-CZ") + " Kč";
}

function formatDate(iso) {
  // Backend posílá "naive" datetime v UTC - doplníme "Z" pro správný převod
  // na místní čas prohlížeče.
  const utcIso = iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z";
  return new Date(utcIso).toLocaleDateString("cs-CZ", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function formatShortDate(iso) {
  return new Date(iso).toLocaleDateString("cs-CZ");
}

export default function PublicOfferPage() {
  const { token } = useParams();
  const [state, setState] = useState("loading"); // loading | ready | not_found | error
  const [offer, setOffer] = useState(null);
  const viewIdRef = useRef(null);
  const startTimeRef = useRef(null);

  useEffect(() => {
    fetchPublicDocument(token)
      .then((data) => {
        setOffer(data.document);
        viewIdRef.current = data.view_id;
        startTimeRef.current = Date.now();
        setState("ready");
      })
      .catch((err) => {
        setState(err.message === "not_found" ? "not_found" : "error");
      });
  }, [token]);

  useEffect(() => {
    function reportDuration() {
      if (!viewIdRef.current || !startTimeRef.current) return;
      const seconds = Math.round((Date.now() - startTimeRef.current) / 1000);
      sendViewDuration(token, viewIdRef.current, seconds);
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "hidden") {
        reportDuration();
      }
    }

    window.addEventListener("beforeunload", reportDuration);
    window.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      window.removeEventListener("beforeunload", reportDuration);
      window.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [token]);

  if (state === "loading") {
    return (
      <div className="offer-state">
        <div className="offer-state-title">Načítám nabídku…</div>
      </div>
    );
  }

  if (state === "not_found") {
    return (
      <div className="offer-state">
        <div className="offer-state-title">Nabídka nenalezena</div>
        <div className="offer-state-text">
          Odkaz je neplatný nebo byla nabídka odstraněna. Kontaktujte prosím svého
          obchodního zástupce.
        </div>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="offer-state">
        <div className="offer-state-title">Něco se nepovedlo</div>
        <div className="offer-state-text">
          Zkuste stránku znovu načíst. Pokud problém přetrvává, kontaktujte nás.
        </div>
      </div>
    );
  }

  const calc = offer.calculation;

  return (
    <div className="offer-shell">
      <div className="offer-header">
        <div className="offer-brand">Nauhel</div>
        <div className="offer-eyebrow">
          {offer.document_type} pro {offer.company_name}
          {offer.version > 1 ? ` · verze ${offer.version}` : ""}
        </div>
        <h1 className="offer-title">{offer.deal_name}</h1>
      </div>

      <div className="offer-card">
        <div className="offer-card-band" />
        <div className="offer-card-body">
          {calc ? (
            <>
              {calc.product_line && (
                <div className="offer-row">
                  <span className="offer-row-label">Produktová řada</span>
                  <span className="offer-row-value">{calc.product_line}</span>
                </div>
              )}
              {calc.wood_species && (
                <div className="offer-row">
                  <span className="offer-row-label">Dřevina</span>
                  <span className="offer-row-value">{calc.wood_species}</span>
                </div>
              )}
              {calc.area_m2 && (
                <div className="offer-row">
                  <span className="offer-row-label">Plocha fasády</span>
                  <span className="offer-row-value mono">{Number(calc.area_m2)} m²</span>
                </div>
              )}

              {calc.items && calc.items.length > 0 && (
                <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 16, marginBottom: 4 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--line)" }}>
                      <th style={{ textAlign: "left", padding: "6px 0", fontSize: 12, color: "var(--ink-600)", fontWeight: 600 }}>Položka</th>
                      <th style={{ textAlign: "right", padding: "6px 0", fontSize: 12, color: "var(--ink-600)", fontWeight: 600 }}>Množství</th>
                      <th style={{ textAlign: "right", padding: "6px 0", fontSize: 12, color: "var(--ink-600)", fontWeight: 600 }}>Jedn. cena</th>
                      <th style={{ textAlign: "right", padding: "6px 0", fontSize: 12, color: "var(--ink-600)", fontWeight: 600 }}>Celkem</th>
                    </tr>
                  </thead>
                  <tbody>
                    {calc.items.map((it, idx) => {
                      const lineTotal = Number(it.quantity) * Number(it.unit_price);
                      return (
                        <tr key={idx} style={{ borderBottom: "1px solid var(--paper-200)" }}>
                          <td style={{ padding: "8px 0", fontSize: 13.5 }}>{it.name}</td>
                          <td className="mono" style={{ padding: "8px 0", fontSize: 13, textAlign: "right" }}>
                            {Number(it.quantity)} {it.unit || ""}
                          </td>
                          <td className="mono" style={{ padding: "8px 0", fontSize: 13, textAlign: "right" }}>
                            {formatMoney(it.unit_price)}
                          </td>
                          <td className="mono" style={{ padding: "8px 0", fontSize: 13, textAlign: "right" }}>
                            {formatMoney(lineTotal)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}

              {(Number(calc.discount_material_percent) > 0 || Number(calc.discount_installation_percent) > 0) && (
                <div style={{ fontSize: 12.5, color: "var(--ink-600)", marginBottom: 8 }}>
                  {Number(calc.discount_material_percent) > 0 && (
                    <div>Sleva na materiál: {Number(calc.discount_material_percent)} %</div>
                  )}
                  {Number(calc.discount_installation_percent) > 0 && (
                    <div>Sleva na montáž: {Number(calc.discount_installation_percent)} %</div>
                  )}
                </div>
              )}

              <div className="offer-row">
                <span className="offer-row-label">Mezisoučet bez DPH</span>
                <span className="offer-row-value mono">{formatMoney(calc.price_without_vat)}</span>
              </div>
              <div className="offer-row">
                <span className="offer-row-label">DPH</span>
                <span className="offer-row-value mono">{formatMoney(calc.vat_amount)}</span>
              </div>
              <div className="offer-total">
                <span className="offer-total-label">Celkem s DPH</span>
                <span className="offer-total-value mono">
                  {formatMoney(calc.price_with_vat)}
                </span>
              </div>
              {calc.valid_until && (
                <div style={{ marginTop: 16, fontSize: 12.5, color: "var(--ink-600)" }}>
                  Nabídka je platná do {formatShortDate(calc.valid_until)}. Uvedené ceny jsou
                  konečné vč. DPH. Nabídka není objednávkou.
                </div>
              )}
            </>
          ) : (
            <div style={{ color: "var(--ink-600)", fontSize: 14 }}>
              Ke stažení nebo detailům se prosím obraťte na svého obchodního zástupce.
            </div>
          )}
        </div>
      </div>

      <div className="offer-card" style={{ marginTop: 16 }}>
        <div className="offer-card-body" style={{ padding: "20px 32px" }}>
          <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ink-600)", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Platební údaje
          </div>
          <div style={{ fontSize: 13, color: "var(--ink-600)", lineHeight: 1.9 }}>
            <div>NAUHEL s.r.o. · Ve Mlejnku 108, 257 65 Čechtice</div>
            <div>IČO: 24463973 · DIČ: CZ24463973</div>
            <div className="mono">Air Bank a.s. · 3599752017/3030</div>
            <div className="mono">IBAN: CZ40 3030 0000 0035 9975 2017</div>
          </div>
        </div>
      </div>

      <div className="offer-footer-note">
        Vytvořeno {formatDate(offer.created_at)} · Nauhel — fasády Yakisugi
      </div>
    </div>
  );
}
