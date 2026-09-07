export const DEAL_STATUSES = [
  "Lead",
  "Kvalifikovaný lead",
  "Nabídka",
  "Objednávka",
  "Zálohová faktura",
  "Vyrobeno",
  "Fakturováno",
  "Ztraceno",
];

// Zrcadlí MANUAL_TRANSITIONS z backendu (app/core/deal_transitions.py) -
// jen pro nabídnutí správného tlačítka v UI, backend je stejně finální autorita.
export const NEXT_MANUAL_STATUS = {
  Lead: "Kvalifikovaný lead",
  "Kvalifikovaný lead": "Nabídka",
  Nabídka: "Objednávka",
  Objednávka: null, // další krok jde jen přes e-signature webhook
  "Zálohová faktura": "Vyrobeno",
  Vyrobeno: "Fakturováno",
  Fakturováno: null,
  Ztraceno: null,
};

export const STATUS_COLORS = {
  Lead: "#9ca3af",
  "Kvalifikovaný lead": "#64748b",
  Nabídka: "#e0b478",
  Objednávka: "#b5652d",
  "Zálohová faktura": "#7a3a1a",
  Vyrobeno: "#2f6f4f",
  Fakturováno: "#1f5c3a",
  Ztraceno: "#a33b3b",
};

// Podle WCAG kontrastu spocita, jestli ma byt text na dane barve pozadi
// bily nebo tmavy - resi spatnou citelnost bileho textu na svetlejsich
// odstinech (napr. Nabidka #e0b478).
export function getBadgeTextColor(hex) {
  const c = hex.replace("#", "");
  const r = parseInt(c.substring(0, 2), 16) / 255;
  const g = parseInt(c.substring(2, 4), 16) / 255;
  const b = parseInt(c.substring(4, 6), 16) / 255;
  const toLinear = (v) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));
  const luminance = 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
  const contrastWithWhite = 1.05 / (luminance + 0.05);
  return contrastWithWhite >= 4.5 ? "#fff" : "var(--ink-900)";
}
