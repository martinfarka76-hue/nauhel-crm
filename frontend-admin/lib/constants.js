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
  Lead: "#8a8578",
  "Kvalifikovaný lead": "#6d8a9c",
  Nabídka: "#b5652d",
  Objednávka: "#c1863f",
  "Zálohová faktura": "#9c8a2d",
  Vyrobeno: "#4f8a5b",
  Fakturováno: "#2d6b4f",
  Ztraceno: "#8a3d3d",
};
