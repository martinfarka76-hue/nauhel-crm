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
  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState("");
  const [confirmName, setConfirmName] = useState("");
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

  function subtotalForCategory(category) {
    if (!calc || !calc.items) return 0;
    return calc.items
      .filter((it) => it.category === category)
      .reduce((sum, it) => sum + Number(it.quantity) * Number(it.unit_price), 0);
  }

  const materialSubtotal = subtotalForCategory("Materiál");
  const installationSubtotal = subtotalForCategory("Práce");
  const materialDiscountAmount = calc
    ? (materialSubtotal * Number(calc.discount_material_percent || 0)) / 100
    : 0;
  const installationDiscountAmount = calc
    ? (installationSubtotal * Number(calc.discount_installation_percent || 0)) / 100
    : 0;

  async function handleConfirmOrder() {
    if (!confirmName.trim()) {
      setConfirmError("Prosím vyplňte své celé jméno.");
      return;
    }
    setConfirming(true);
    setConfirmError("");
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18080";
      const res = await fetch(`${API_URL}/public/documents/${token}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmed_by_name: confirmName.trim() }),
      });
      if (!res.ok) throw new Error("Potvrzení se nezdařilo, zkuste to prosím znovu.");
      const data = await res.json();
      setOffer((prev) => ({ ...prev, confirmed_at: data.confirmed_at, confirmed_by_name: data.confirmed_by_name }));
    } catch (err) {
      setConfirmError(err.message);
    } finally {
      setConfirming(false);
    }
  }

  return (
    <div className="offer-shell">
      <div className="offer-header">
        <div className="offer-brand">Nauhel</div>
        <div className="offer-eyebrow">
          {offer.document_type} pro {offer.company_name}
          {offer.version > 1 ? ` · verze ${offer.version}` : ""}
        </div>
        <h1 className="offer-title">{offer.deal_name}</h1>
        {(offer.company_ico || offer.company_dic || offer.company_address) && (
          <div style={{ fontSize: 12.5, color: "var(--ink-600)", marginTop: 4 }}>
            {offer.company_address && <div>{offer.company_address}</div>}
            <div>
              {offer.company_ico && `IČO: ${offer.company_ico}`}
              {offer.company_ico && offer.company_dic && " · "}
              {offer.company_dic && `DIČ: ${offer.company_dic}`}
            </div>
          </div>
        )}
      </div>

      {offer.document_type === "Objednávka" && (
        <div
          style={{
            border: offer.confirmed_at ? "2px solid var(--success, #3d7a4f)" : "2px solid var(--ember-500)",
            background: offer.confirmed_at ? "#f0f7f2" : "#fdf3ec",
            borderRadius: 12,
            padding: "22px 28px",
            marginBottom: 20,
            textAlign: "center",
          }}
        >
          {offer.confirmed_at ? (
            <div>
              <div style={{ fontSize: 17, fontWeight: 700, color: "var(--success, #3d7a4f)", marginBottom: 4 }}>
                ✓ Objednávka potvrzena
              </div>
              <div style={{ fontSize: 13, color: "var(--ink-600)" }}>
                Potvrdil(a) {offer.confirmed_by_name} dne {formatDate(offer.confirmed_at)}. Děkujeme, brzy
                se vám ozveme s dalšími kroky.
              </div>
            </div>
          ) : (
            <>
              <div style={{ fontSize: 16, fontWeight: 700, color: "var(--ember-600, #9c5424)", marginBottom: 8 }}>
                ⚠ Vyžaduje vaše potvrzení
              </div>
              <div style={{ fontSize: 13.5, color: "var(--ink-600)", marginBottom: 14 }}>
                Vyplňte prosím své celé jméno a kliknutím na tlačítko níže elektronicky potvrďte
                tuto objednávku.
              </div>
              <input
                type="text"
                value={confirmName}
                onChange={(e) => setConfirmName(e.target.value)}
                placeholder="Celé jméno"
                style={{
                  width: "100%",
                  maxWidth: 300,
                  padding: "10px 14px",
                  fontSize: 14.5,
                  border: "1px solid var(--line)",
                  borderRadius: 8,
                  marginBottom: 14,
                  textAlign: "center",
                }}
              />
              <div>
                <button
                  onClick={handleConfirmOrder}
                  disabled={confirming}
                  style={{
                    background: "var(--ember-500)",
                    color: "#fff",
                    border: "none",
                    borderRadius: 8,
                    padding: "13px 32px",
                    fontSize: 15,
                    fontWeight: 700,
                    cursor: confirming ? "default" : "pointer",
                  }}
                >
                  {confirming ? "Potvrzuji…" : "Potvrdit objednávku"}
                </button>
              </div>
              {confirmError && (
                <div style={{ marginTop: 10, fontSize: 12.5, color: "#a13d3d" }}>{confirmError}</div>
              )}
            </>
          )}
        </div>
      )}

      <div className="offer-card">
        <div className="offer-card-band" />
        <div className="offer-card-body">
          {calc ? (
            <>
              {(calc.product_line || calc.wood_species || calc.area_m2) && (
                <div className="offer-stats">
                  {calc.product_line && (
                    <div className="offer-stat">
                      <div className="offer-stat-label">Produktová řada</div>
                      <div className="offer-stat-value">{calc.product_line}</div>
                    </div>
                  )}
                  {calc.wood_species && (
                    <div className="offer-stat">
                      <div className="offer-stat-label">Dřevina</div>
                      <div className="offer-stat-value">{calc.wood_species}</div>
                    </div>
                  )}
                  {calc.area_m2 && (
                    <div className="offer-stat">
                      <div className="offer-stat-label">Plocha fasády</div>
                      <div className="offer-stat-value mono">{Number(calc.area_m2)} m²</div>
                    </div>
                  )}
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
                    <div>
                      Sleva na materiál: {Number(calc.discount_material_percent)} %
                      {" "}(−{formatMoney(materialDiscountAmount)})
                    </div>
                  )}
                  {Number(calc.discount_installation_percent) > 0 && (
                    <div>
                      Sleva na montáž: {Number(calc.discount_installation_percent)} %
                      {" "}(−{formatMoney(installationDiscountAmount)})
                    </div>
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
              <div style={{ marginTop: 10, fontSize: 11.5, color: "var(--ink-400)", lineHeight: 1.6 }}>
                Jedná se o zakázkovou výrobu na míru dle individuálních požadavků zákazníka. V
                souladu s § 1837 písm. d) občanského zákoníku (zák. č. 89/2012 Sb.) nelze v
                případě zboží vyrobeného podle požadavků spotřebitele nebo přizpůsobeného jeho
                osobním potřebám odstoupit od smlouvy uzavřené distančním způsobem bez uvedení
                důvodu.
              </div>
            </>
          ) : (
            <div style={{ color: "var(--ink-600)", fontSize: 14 }}>
              Ke stažení nebo detailům se prosím obraťte na svého obchodního zástupce.
            </div>
          )}
        </div>
      </div>

      {calc && (calc.delivery_terms || calc.payment_terms) && (
        <div className="offer-card" style={{ marginTop: 16 }}>
          <div className="offer-card-body" style={{ padding: "20px 32px" }}>
            {calc.delivery_terms && (
              <div style={{ marginBottom: calc.payment_terms ? 12 : 0 }}>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ink-600)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Termín realizace
                </div>
                <div style={{ fontSize: 13.5 }}>{calc.delivery_terms}</div>
              </div>
            )}
            {calc.payment_terms && (
              <div>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ink-600)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Platební podmínky
                </div>
                <div style={{ fontSize: 13.5 }}>{calc.payment_terms}</div>
              </div>
            )}
          </div>
        </div>
      )}

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
