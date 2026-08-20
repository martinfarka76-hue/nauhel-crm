"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { fetchPublicDocument, sendViewDuration } from "@/lib/api";

function formatMoney(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("cs-CZ") + " Kč";
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("cs-CZ", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
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
              {calc.unit_price_per_m2 && (
                <div className="offer-row">
                  <span className="offer-row-label">Cena za m²</span>
                  <span className="offer-row-value mono">
                    {formatMoney(calc.unit_price_per_m2)}
                  </span>
                </div>
              )}
              {calc.price_without_vat && (
                <div className="offer-row">
                  <span className="offer-row-label">Cena bez DPH</span>
                  <span className="offer-row-value mono">
                    {formatMoney(calc.price_without_vat)}
                  </span>
                </div>
              )}
              {calc.vat_amount && (
                <div className="offer-row">
                  <span className="offer-row-label">DPH</span>
                  <span className="offer-row-value mono">{formatMoney(calc.vat_amount)}</span>
                </div>
              )}
              <div className="offer-total">
                <span className="offer-total-label">Celkem s DPH</span>
                <span className="offer-total-value mono">
                  {formatMoney(calc.price_with_vat)}
                </span>
              </div>
            </>
          ) : (
            <div style={{ color: "var(--ink-600)", fontSize: 14 }}>
              Ke stažení nebo detailům se prosím obraťte na svého obchodního zástupce.
            </div>
          )}
        </div>
      </div>

      <div className="offer-footer-note">
        Vytvořeno {formatDate(offer.created_at)} · Nauhel — fasády Yakisugi
      </div>
    </div>
  );
}
