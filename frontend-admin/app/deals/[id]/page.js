"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import ProtectedShell from "@/components/ProtectedShell";
import { api } from "@/lib/api";
import { STATUS_COLORS, NEXT_MANUAL_STATUS } from "@/lib/constants";

const PUBLIC_URL = process.env.NEXT_PUBLIC_PUBLIC_URL || "http://localhost:18082";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18080";

function getDefaultValidUntil() {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  return d.toISOString().slice(0, 10);
}
const CATEGORIES = ["Materiál", "Práce", "Doprava", "Ostatní"];
const PRODUCT_LINES = ["Atacama", "Mirage", "Ocaso"];

const TRANSITION_EXPLANATIONS = {
  "Kvalifikovaný lead":
    'Přesunout případ do stavu "Kvalifikovaný lead"? Jen posuneš pipeline dál - nic se ' +
    "automaticky nevytváří ani neodesílá.",
  Nabídka:
    "Vytvoří se nabídka a automaticky se odešle zákazníkovi e-mailem (pokud má odpovědný " +
    "kontakt vyplněný e-mail). Zkontroluj prosím, že kalkulace obsahuje správné položky a ceny.",
  Objednávka:
    "Tímto potvrzuješ, že zákazník nabídku přijal. Vytvoří se objednávka a odešle se " +
    "zákazníkovi e-mailem s odkazem na elektronické potvrzení. Jakmile ji zákazník potvrdí, " +
    "případ se automaticky posune na Zálohovou fakturu.",
  Vyrobeno:
    "⚠️ Automaticky se vygeneruje PDF dodacího listu (s údaji z aktivní kalkulace) a nahraje se na " +
    "SharePoint do složky 03_Realizace. Přesuň případ, až bude zakázka hotová a připravená k předání " +
    "zákazníkovi.",
  Fakturováno:
    "Vytvoří se záznam pro finální fakturu (tu pak nahraješ jako PDF v sekci Dokumenty, " +
    "stejně jako u zálohové faktury). Zaznamená se dnešní datum jako datum fakturace.",
  Ztraceno:
    'Označit tento případ jako "Ztraceno"? Nic se automaticky nemaže ani neodesílá - stav lze ' +
    "později kdykoliv ručně vrátit zpět.",
};

function formatDate(iso) {
  if (!iso) return "—";
  const utcIso = iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z";
  return new Date(utcIso).toLocaleString("cs-CZ");
}

function formatDateOnly(dateStr) {
  // Datum bez času (YYYY-MM-DD) - rozparsujeme ručně, ať se vyhneme
  // timezone posunu, který by mohl nastat přes new Date().
  if (!dateStr) return "—";
  const [y, m, d] = dateStr.split("-");
  return `${d}.${m}.${y}`;
}

// Datum uzavření lze ručně editovat jen do stavu Nabídka - jakmile Deal
// dosáhne Objednávky, datum se zamkne na skutečné datum uzavření.
const CLOSE_DATE_EDITABLE_STATUSES = ["Lead", "Kvalifikovaný lead", "Nabídka"];
// Datum fakturace lze editovat jako odhad, dokud Deal nedosáhne stavu Fakturováno.
const INVOICE_DATE_LOCKED_STATUS = "Fakturováno";

function money(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("cs-CZ") + " Kč";
}

const emptyItemForm = { category: "Materiál", name: "", unit: "", quantity: "", unit_price: "" };
const DEFAULT_WOOD_SPECIES_NAME = 'Modřín Evropský "Z" 20x145, délka 4000mm';

export default function DealDetailPage() {
  const { id } = useParams();
  const [deal, setDeal] = useState(null);
  const [company, setCompany] = useState(null);
  const [companyContacts, setCompanyContacts] = useState([]);
  const [users, setUsers] = useState([]);
  const [calculations, setCalculations] = useState([]);
  const [calcItems, setCalcItems] = useState({}); // { [calcId]: [items] }
  const [woodSpeciesList, setWoodSpeciesList] = useState([]);
  const [pricingParams, setPricingParams] = useState({}); // { [key]: value }
  const [documents, setDocuments] = useState([]);
  const [documentViews, setDocumentViews] = useState({});
  const [expandedDoc, setExpandedDoc] = useState(null);
  const [copiedDoc, setCopiedDoc] = useState(null);
  const [uploadingInvoiceId, setUploadingInvoiceId] = useState(null);
  const [sendingInvoiceId, setSendingInvoiceId] = useState(null);
  const [copiedInvoiceLineId, setCopiedInvoiceLineId] = useState(null);
  const [attachments, setAttachments] = useState([]);
  const [notes, setNotes] = useState([]);
  const [newNoteText, setNewNoteText] = useState("");
  const [addingNote, setAddingNote] = useState(false);
  const [uploadingAttachment, setUploadingAttachment] = useState(false);
  const [showAttachments, setShowAttachments] = useState(false);
  const [showActionsMenu, setShowActionsMenu] = useState(false);
  const actionsMenuRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (actionsMenuRef.current && !actionsMenuRef.current.contains(e.target)) {
        setShowActionsMenu(false);
      }
    }
    if (showActionsMenu) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [showActionsMenu]);
  const [error, setError] = useState("");
  const [transitioning, setTransitioning] = useState(false);

  const [showCalcForm, setShowCalcForm] = useState(false);
  const [calcSaving, setCalcSaving] = useState(false);
  const [calcForm, setCalcForm] = useState({
    product_line: "",
    wood_species: "",
    area_m2: "",
    distance_km: "",
    vat_rate: "0.21",
    discount_material_percent: "0",
    discount_installation_percent: "0",
    deposit_percent: "50",
    valid_until: getDefaultValidUntil(),
    delivery_terms: "6-8 týdnů od objednávky",
    payment_terms: "Zálohová faktura 50 % vystavena po potvrzení objednávky, finální faktura se splatností dnem dodání",
  });

  const [itemForms, setItemForms] = useState({}); // { [calcId]: itemForm }
  const [expandedCalcs, setExpandedCalcs] = useState({}); // { [calcId]: bool }
  const [editingItemId, setEditingItemId] = useState(null);
  const [editingCalcId, setEditingCalcId] = useState(null);
  const [editCalcForm, setEditCalcForm] = useState(null);
  const [editItemForm, setEditItemForm] = useState(emptyItemForm);

  const [editingDeal, setEditingDeal] = useState(false);
  const [dealEditForm, setDealEditForm] = useState(null);

  function loadAll() {
    api
      .get(`/deals/${id}`)
      .then((d) => {
        setDeal(d);
        return Promise.all([
          api.get(`/companies/${d.company_id}`),
          api.get(`/contacts?company_id=${d.company_id}`),
          api.get(`/users`),
          api.get(`/deals/${id}/calculations`),
          api.get(`/deals/${id}/documents`),
          api.get(`/deals/${id}/attachments`),
          api.get(`/deals/${id}/notes`),
        ]);
      })
      .then(async ([c, dealContacts, usersData, calcs, docs, attachmentsData, notesData]) => {
        setCompany(c);
        setCompanyContacts(dealContacts);
        setUsers(usersData);
        setCalculations(calcs);
        setDocuments(docs);
        setAttachments(attachmentsData);
        setNotes(notesData);
        const itemsEntries = await Promise.all(
          calcs.map(async (calc) => [calc.id, await api.get(`/calculations/${calc.id}/items`)])
        );
        setCalcItems(Object.fromEntries(itemsEntries));
      })
      .catch((err) => setError(err.message));
  }

  useEffect(loadAll, [id]);

  useEffect(() => {
    Promise.all([api.get("/wood-species"), api.get("/pricing-parameters")])
      .then(([speciesData, paramsData]) => {
        setWoodSpeciesList(speciesData);
        const map = {};
        paramsData.forEach((p) => (map[p.key] = Number(p.value)));
        setPricingParams(map);
      })
      .catch(() => {
        // Nekritické - formulář položky bude fungovat i bez předvyplňování
      });
  }, []);

  function handleCopyLink(accessToken, docId) {
    const url = `${PUBLIC_URL}/n/${accessToken}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopiedDoc(docId);
      setTimeout(() => setCopiedDoc(null), 2000);
    });
  }

  function getAuthToken() {
    return typeof window !== "undefined" ? localStorage.getItem("nauhel_token") : null;
  }

  async function handleUploadInvoice(documentId, file) {
    if (!file) return;
    setUploadingInvoiceId(documentId);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_URL}/documents/${documentId}/invoice-pdf`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getAuthToken()}` },
        body: formData,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Nahrání faktury selhalo.");
      }
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploadingInvoiceId(null);
    }
  }

  async function handleDownloadInvoice(documentId) {
    setError("");
    try {
      const res = await fetch(`${API_URL}/documents/${documentId}/invoice-pdf`, {
        headers: { Authorization: `Bearer ${getAuthToken()}` },
      });
      if (!res.ok) throw new Error("Stažení faktury selhalo.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "faktura.pdf";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDownloadDeliveryNote(documentId) {
    setError("");
    try {
      const res = await fetch(`${API_URL}/documents/${documentId}/delivery-note`, {
        headers: { Authorization: `Bearer ${getAuthToken()}` },
      });
      if (!res.ok) throw new Error("Stažení dodacího listu selhalo.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "dodaci_list.pdf";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSendInvoiceEmail(documentId) {
    if (!window.confirm("Odeslat fakturu zákazníkovi emailem (odkaz + PDF příloha)?")) return;
    setSendingInvoiceId(documentId);
    setError("");
    try {
      await api.post(`/documents/${documentId}/send-invoice-email`, {});
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setSendingInvoiceId(null);
    }
  }

  async function handleAddNote() {
    if (!newNoteText.trim()) return;
    setAddingNote(true);
    setError("");
    try {
      await api.post(`/deals/${id}/notes`, { content: newNoteText.trim() });
      setNewNoteText("");
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setAddingNote(false);
    }
  }

  async function handleUploadAttachment(file) {
    setUploadingAttachment(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_URL}/deals/${id}/attachments`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getAuthToken()}` },
        body: formData,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Nahrání přílohy selhalo.");
      }
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploadingAttachment(false);
    }
  }

  async function handleDownloadAttachment(attachmentId, filename) {
    setError("");
    try {
      const res = await fetch(`${API_URL}/attachments/${attachmentId}/download`, {
        headers: { Authorization: `Bearer ${getAuthToken()}` },
      });
      if (!res.ok) throw new Error("Stažení přílohy selhalo.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename || "priloha";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteAttachment(attachmentId) {
    if (!window.confirm("Smazat tuto přílohu? (Tato akce je nevratná v CRM, soubor na SharePointu zůstane.)")) return;
    setError("");
    try {
      await api.delete(`/attachments/${attachmentId}`);
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleToggleViews(docId) {
    if (expandedDoc === docId) {
      setExpandedDoc(null);
      return;
    }
    setExpandedDoc(docId);
    await refreshViews(docId);
  }

  async function refreshViews(docId) {
    setDocumentViews((prev) => ({ ...prev, [docId]: undefined }));
    try {
      const views = await api.get(`/documents/${docId}/views`);
      setDocumentViews((prev) => ({ ...prev, [docId]: views }));
    } catch (err) {
      setError(err.message);
    }
  }

  function startEditDeal() {
    setDealEditForm({
      name: deal.name,
      price: deal.price != null ? String(deal.price) : "",
      contact_id: deal.contact_id || "",
      owner_user_id: deal.owner_user_id || "",
      expected_close_date: deal.expected_close_date || "",
      expected_invoice_date: deal.expected_invoice_date || "",
      deposit_paid: deal.deposit_paid,
    });
    setEditingDeal(true);
  }

  async function handleSaveDeal(e) {
    e.preventDefault();
    setError("");
    try {
      await api.put(`/deals/${id}`, {
        name: dealEditForm.name,
        price: dealEditForm.price ? Number(dealEditForm.price) : null,
        contact_id: dealEditForm.contact_id || null,
        owner_user_id: dealEditForm.owner_user_id || null,
        expected_close_date: dealEditForm.expected_close_date || null,
        expected_invoice_date: dealEditForm.expected_invoice_date || null,
        deposit_paid: dealEditForm.deposit_paid,
      });
      setEditingDeal(false);
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteDeal() {
    if (!window.confirm(`Opravdu smazat obchodní případ "${deal.name}"? Tato akce je nevratná.`)) return;
    setError("");
    try {
      await api.delete(`/deals/${id}`);
      window.location.href = company ? `/companies/${company.id}` : "/companies";
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCreateNewOfferVersion() {
    const activeCalc = calculations.find((c) => c.is_active);
    if (!activeCalc) {
      setError("Nejdřív musí existovat aktivní kalkulace, na kterou se má nabídka navázat.");
      return;
    }
    const existingOffers = documents.filter((d) => d.document_type === "Nabídka");
    const nextVersion = existingOffers.length + 1;
    const willAutoTransition = deal.status === "Lead" || deal.status === "Kvalifikovaný lead";
    const statusNote = willAutoTransition
      ? ` Případ zároveň automaticky přejde do stavu "Nabídka" (aktuálně je "${deal.status}").`
      : "";
    if (
      !window.confirm(
        `Vytvořit novou verzi nabídky (v${nextVersion}) navázanou na aktuálně aktivní kalkulaci ` +
          `("${activeCalc.product_line || "—"}")? Starší verze zůstanou dostupné se svými odkazy, ` +
          `nová bude označena jako Aktuální.${statusNote}`
      )
    )
      return;
    setError("");
    try {
      await api.post(`/deals/${id}/documents`, {
        calculation_id: activeCalc.id,
        document_type: "Nabídka",
        version: nextVersion,
      });
      loadAll();
      if (willAutoTransition) {
        alert('Nabídka byla vytvořena a případ byl automaticky přesunut do stavu "Nabídka".');
      }
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleTransition(toStatus) {
    const explanation = TRANSITION_EXPLANATIONS[toStatus] || `Opravdu chceš přesunout případ do stavu "${toStatus}"?`;
    if (!window.confirm(explanation)) return;

    setTransitioning(true);
    setError("");
    try {
      await api.post(`/deals/${id}/transition`, { to_status: toStatus });
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setTransitioning(false);
    }
  }

  async function handleCreateCalculation(e) {
    e.preventDefault();
    setCalcSaving(true);
    setError("");
    try {
      const newCalc = await api.post(`/deals/${id}/calculations`, {
        product_line: calcForm.product_line || null,
        wood_species: calcForm.wood_species || null,
        area_m2: calcForm.area_m2 ? Number(calcForm.area_m2) : null,
        distance_km: calcForm.distance_km ? Number(calcForm.distance_km) : null,
        vat_rate: Number(calcForm.vat_rate) || 0,
        discount_material_percent: Number(calcForm.discount_material_percent) || 0,
        discount_installation_percent: Number(calcForm.discount_installation_percent) || 0,
        deposit_percent: Number(calcForm.deposit_percent) || 50,
        valid_until: calcForm.valid_until || null,
        delivery_terms: calcForm.delivery_terms || null,
        payment_terms: calcForm.payment_terms || null,
      });
      setExpandedCalcs((prev) => ({ ...prev, [newCalc.id]: true }));
      setCalcForm({
        product_line: "",
        wood_species: "",
        area_m2: "",
        distance_km: "",
        vat_rate: "0.21",
        discount_material_percent: "0",
        discount_installation_percent: "0",
        deposit_percent: "50",
        valid_until: getDefaultValidUntil(),
        delivery_terms: "6-8 týdnů od objednávky",
        payment_terms: "Zálohová faktura 50 % vystavena po potvrzení objednávky, finální faktura se splatností dnem dodání",
      });
      setShowCalcForm(false);
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setCalcSaving(false);
    }
  }

  function getItemForm(calcId) {
    return itemForms[calcId] || emptyItemForm;
  }

  function setItemForm(calcId, patch) {
    setItemForms((prev) => ({ ...prev, [calcId]: { ...getItemForm(calcId), ...patch } }));
  }

  function surchargeKeyForProductLine(productLine) {
    if (!productLine) return null;
    const slug = productLine.toLowerCase();
    return `surcharge_${slug}_per_m2`;
  }

  function handleApplyWoodSpecies(calcId, speciesId, productLine, areaM2) {
    const species = woodSpeciesList.find((s) => s.id === speciesId);
    if (!species) return;
    const marginMaterial = pricingParams.margin_material ?? 0;
    const surchargeKey = surchargeKeyForProductLine(productLine);
    const surcharge = surchargeKey ? pricingParams[surchargeKey] ?? 0 : 0;
    const basePrice = Number(species.purchase_price_per_m2) || 0;
    const suggestedPrice = Math.round((basePrice * (1 + marginMaterial) + surcharge) * 100) / 100;

    setItemForm(calcId, {
      category: "Materiál",
      name: species.name,
      unit: "m²",
      quantity: areaM2 ? String(Number(areaM2)) : getItemForm(calcId).quantity,
      unit_price: String(suggestedPrice),
    });
  }

  function handleCalculateTransport(calcId, distanceKm) {
    if (!distanceKm) {
      setError("Kalkulace nemá vyplněnou vzdálenost (km) - doplň ji v hlavičce kalkulace.");
      return;
    }
    const fuel = pricingParams.fuel_price_per_km ?? 0;
    const driver = pricingParams.driver_price_per_km ?? 0;
    const fixedCost = pricingParams.transport_fixed_to_customer ?? 0;
    const distance = Number(distanceKm);
    const total = distance * (fuel + driver) + fixedCost;
    // Jednotka "km" - jednotková cena je celková cena rozpočítaná na km (včetně
    // fixního nákladu), ať součet (množství × jedn. cena) sedí na celkovou částku.
    const unitPrice = distance > 0 ? Math.round((total / distance) * 100) / 100 : 0;

    setItemForm(calcId, {
      category: "Doprava",
      name: "Doprava k zákazníkovi",
      unit: "km",
      quantity: String(distance),
      unit_price: String(unitPrice),
    });
  }

  function handleApplyInstallation(calcId, areaM2) {
    const price = pricingParams.installation_price_per_m2 ?? 0;
    setItemForm(calcId, {
      category: "Práce",
      name: "Montáž",
      unit: "m²",
      quantity: areaM2 ? String(Number(areaM2)) : getItemForm(calcId).quantity,
      unit_price: String(price),
    });
  }

  function handleCategoryChange(calcId, newCategory, calc) {
    if (newCategory === "Materiál") {
      const defaultSpecies = woodSpeciesList.find((s) => s.name === DEFAULT_WOOD_SPECIES_NAME);
      if (defaultSpecies) {
        handleApplyWoodSpecies(calcId, defaultSpecies.id, calc.product_line, calc.area_m2);
        return;
      }
    }
    if (newCategory === "Práce") {
      handleApplyInstallation(calcId, calc.area_m2);
      return;
    }
    if (newCategory === "Doprava") {
      if (calc.distance_km) {
        handleCalculateTransport(calcId, calc.distance_km);
      } else {
        setItemForm(calcId, { category: "Doprava", name: "Doprava k zákazníkovi", unit: "km" });
      }
      return;
    }
    setItemForm(calcId, { category: newCategory });
  }

  async function handleAddItem(calcId) {
    const form = getItemForm(calcId);
    if (!form.name || !form.quantity || !form.unit_price) {
      setError("Vyplň prosím název, množství a jednotkovou cenu položky.");
      return;
    }
    setError("");
    try {
      const updatedCalc = await api.post(`/calculations/${calcId}/items`, {
        category: form.category,
        name: form.name,
        unit: form.unit || null,
        quantity: Number(form.quantity),
        unit_price: Number(form.unit_price),
        display_order: (calcItems[calcId] || []).length,
      });
      setCalculations((prev) => prev.map((c) => (c.id === calcId ? updatedCalc : c)));
      const items = await api.get(`/calculations/${calcId}/items`);
      setCalcItems((prev) => ({ ...prev, [calcId]: items }));
      setItemForms((prev) => ({ ...prev, [calcId]: emptyItemForm }));
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteItem(calcId, itemId) {
    setError("");
    try {
      const updatedCalc = await api.delete(`/calculation-items/${itemId}`);
      setCalculations((prev) => prev.map((c) => (c.id === calcId ? updatedCalc : c)));
      const items = await api.get(`/calculations/${calcId}/items`);
      setCalcItems((prev) => ({ ...prev, [calcId]: items }));
    } catch (err) {
      setError(err.message);
    }
  }

  function startEditCalc(c) {
    setEditingCalcId(c.id);
    setEditCalcForm({
      product_line: c.product_line || "",
      wood_species: c.wood_species || "",
      area_m2: c.area_m2 ?? "",
      distance_km: c.distance_km ?? "",
      vat_rate: c.vat_rate != null ? String(c.vat_rate) : "0.21",
      discount_material_percent: c.discount_material_percent != null ? String(c.discount_material_percent) : "0",
      discount_installation_percent:
        c.discount_installation_percent != null ? String(c.discount_installation_percent) : "0",
      deposit_percent: c.deposit_percent != null ? String(c.deposit_percent) : "50",
      valid_until: c.valid_until || "",
      delivery_terms: c.delivery_terms || "",
      payment_terms: c.payment_terms || "",
    });
  }

  async function handleSaveCalc(calcId) {
    setError("");
    try {
      const updatedCalc = await api.put(`/calculations/${calcId}`, {
        product_line: editCalcForm.product_line || null,
        wood_species: editCalcForm.wood_species || null,
        area_m2: editCalcForm.area_m2 ? Number(editCalcForm.area_m2) : null,
        distance_km: editCalcForm.distance_km ? Number(editCalcForm.distance_km) : null,
        vat_rate: Number(editCalcForm.vat_rate) || 0,
        discount_material_percent: Number(editCalcForm.discount_material_percent) || 0,
        discount_installation_percent: Number(editCalcForm.discount_installation_percent) || 0,
        deposit_percent: Number(editCalcForm.deposit_percent) || 50,
        valid_until: editCalcForm.valid_until || null,
        delivery_terms: editCalcForm.delivery_terms || null,
        payment_terms: editCalcForm.payment_terms || null,
      });
      setCalculations((prev) => prev.map((c) => (c.id === calcId ? updatedCalc : c)));
      setEditingCalcId(null);
    } catch (err) {
      setError(err.message);
    }
  }

  function toggleCalcExpanded(calcId) {
    setExpandedCalcs((prev) => ({ ...prev, [calcId]: !prev[calcId] }));
  }

  function startEditItem(item) {
    setEditingItemId(item.id);
    setEditItemForm({
      category: item.category,
      name: item.name,
      unit: item.unit || "",
      quantity: String(item.quantity),
      unit_price: String(item.unit_price),
    });
  }

  function cancelEditItem() {
    setEditingItemId(null);
    setEditItemForm(emptyItemForm);
  }

  async function handleSaveEditItem(calcId, itemId) {
    setError("");
    try {
      const updatedCalc = await api.put(`/calculation-items/${itemId}`, {
        category: editItemForm.category,
        name: editItemForm.name,
        unit: editItemForm.unit || null,
        quantity: Number(editItemForm.quantity),
        unit_price: Number(editItemForm.unit_price),
      });
      setCalculations((prev) => prev.map((c) => (c.id === calcId ? updatedCalc : c)));
      const items = await api.get(`/calculations/${calcId}/items`);
      setCalcItems((prev) => ({ ...prev, [calcId]: items }));
      cancelEditItem();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!deal) {
    return (
      <ProtectedShell>
        {error ? <div className="error-banner">{error}</div> : <div className="empty-state">Načítám…</div>}
      </ProtectedShell>
    );
  }

  const nextStatus = NEXT_MANUAL_STATUS[deal.status];

  const activeCalc = calculations.find((c) => c.is_active);
  const activeCalcItems = activeCalc ? calcItems[activeCalc.id] || [] : [];
  const latestObjednavka = documents
    .filter((d) => d.document_type === "Objednávka")
    .sort((a, b) => b.version - a.version)[0];
  const latestZalohova = documents.find((d) => d.document_type === "Zálohová faktura");
  const latestFinalni = documents.find((d) => d.document_type === "Finální faktura");

  function scrollToSection(sectionId) {
    document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function getGuidance() {
    if (deal.status === "Ztraceno") {
      return {
        title: "Případ je označen jako ztracený",
        description: 'Pokud se situace změní, stav lze ručně upravit z menu "⋯" nahoře.',
      };
    }
    if (deal.status === "Lead" || deal.status === "Kvalifikovaný lead") {
      if (!activeCalc) {
        return {
          title: "Vytvořte cenovou kalkulaci",
          description: "Než půjde vytvořit nabídka, je potřeba spočítat cenu - materiál, práci a dopravu.",
          actionLabel: "+ Nová kalkulace",
          action: () => {
            setShowCalcForm(true);
            scrollToSection("kalkulace-section");
          },
        };
      }
      if (activeCalcItems.length === 0) {
        return {
          title: "Přidejte položky kalkulace",
          description: "Kalkulace je založená, ale zatím nemá žádné položky - bez nich nejde spočítat cena.",
          actionLabel: "Otevřít kalkulaci",
          action: () => {
            setExpandedCalcs((prev) => ({ ...prev, [activeCalc.id]: true }));
            scrollToSection("kalkulace-section");
          },
        };
      }
      if (deal.status === "Lead") {
        return {
          title: "Přesuňte případ do Kvalifikovaného leadu",
          description: "Kalkulace je připravená. Dalším krokem je posunout případ dál v pipeline.",
          actionLabel: "Přesunout do: Kvalifikovaný lead",
          action: () => handleTransition("Kvalifikovaný lead"),
        };
      }
      return {
        title: "Vytvořte nabídku pro zákazníka",
        description:
          'Kalkulace je připravená. Kliknutím na "Přesunout do: Nabídka" se automaticky vygeneruje veřejný odkaz ' +
          "a odešle e-mail zákazníkovi (pokud má odpovědný kontakt vyplněný e-mail).",
        actionLabel: "Přesunout do: Nabídka",
        action: () => handleTransition("Nabídka"),
      };
    }
    if (deal.status === "Nabídka") {
      return {
        title: "Nabídka odeslána - čekáte na odpověď zákazníka",
        description: "Až se zákazník ozve a bude s nabídkou souhlasit, ručně přesuňte případ do stavu Objednávka.",
        actionLabel: "Přesunout do: Objednávka",
        action: () => handleTransition("Objednávka"),
      };
    }
    if (deal.status === "Objednávka") {
      if (!latestObjednavka?.confirmed_at) {
        return {
          title: "Čeká se na elektronické potvrzení objednávky",
          description:
            "Zákazník dostal e-mail s odkazem na potvrzení objednávky. Jakmile ji potvrdí, automaticky " +
            "vznikne zálohová faktura a případ se posune dál.",
        };
      }
      return {
        title: "Objednávka potvrzena",
        description:
          "Zálohová faktura vznikne automaticky během pár vteřin. Pokud se stav neaktualizuje, " +
          "obnov stránku a zkontroluj sekci Dokumenty níže.",
        actionLabel: "Zobrazit dokumenty",
        action: () => scrollToSection("dokumenty-section"),
      };
    }
    if (deal.status === "Zálohová faktura") {
      if (!latestZalohova?.invoice_pdf_filename) {
        return {
          title: "Nahrajte zálohovou fakturu",
          description: "Zákazník potvrdil objednávku. Vystavte zálohovou fakturu (např. ručně v iDokladu) a nahrajte ji sem jako PDF.",
          actionLabel: "Přejít na fakturu",
          action: () => scrollToSection("dokumenty-section"),
        };
      }
      if (!latestZalohova?.invoice_sent_at) {
        return {
          title: "Odešlete zálohovou fakturu zákazníkovi",
          description: "Faktura je nahraná - stačí ji odeslat e-mailem (odkaz i PDF příloha).",
          actionLabel: "Přejít na fakturu",
          action: () => scrollToSection("dokumenty-section"),
        };
      }
      return {
        title: "Čeká se na zaplacení zálohy",
        description: "Jakmile zákazník zálohu zaplatí, přesuň případ do stavu Vyrobeno.",
        actionLabel: "Přesunout do: Vyrobeno",
        action: () => handleTransition("Vyrobeno"),
      };
    }
    if (deal.status === "Vyrobeno") {
      return {
        title: "Zakázka se vyrábí",
        description:
          "Dodací list byl automaticky vygenerován (viz sekce Dokumenty) a nahrán na SharePoint. " +
          "Až bude zakázka hotová a předaná zákazníkovi, přesuň případ do stavu Fakturováno.",
        actionLabel: "Přesunout do: Fakturováno",
        action: () => handleTransition("Fakturováno"),
      };
    }
    if (deal.status === "Fakturováno") {
      if (!latestFinalni?.invoice_pdf_filename) {
        return {
          title: "Nahrajte finální fakturu",
          description: "Vystavte finální fakturu (např. ručně v iDokladu) a nahrajte ji sem jako PDF.",
          actionLabel: "Přejít na fakturu",
          action: () => scrollToSection("dokumenty-section"),
        };
      }
      return {
        title: "Případ je kompletně vyřízen",
        description: "Kalkulace, nabídka, objednávka i fakturace jsou hotové. Žádná další akce není potřeba.",
      };
    }
    return null;
  }

  const guidance = getGuidance();

  return (
    <ProtectedShell>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 className="page-title">{deal.name}</h1>
          <p className="page-subtitle">
            {company ? (
              <a href={`/companies/${company.id}`} style={{ textDecoration: "underline" }}>
                {company.name}
              </a>
            ) : (
              "—"
            )}
          </p>
          <div style={{ fontSize: 12.5, color: "var(--ink-600)", display: "flex", gap: 16, marginTop: -8, marginBottom: 4 }}>
            <span>
              {CLOSE_DATE_EDITABLE_STATUSES.includes(deal.status) ? "Odhad uzavření" : "Uzavřeno"}:{" "}
              <strong>{formatDateOnly(deal.expected_close_date)}</strong>
            </span>
            <span>
              {deal.status === INVOICE_DATE_LOCKED_STATUS ? "Fakturováno" : "Odhad fakturace"}:{" "}
              <strong>{formatDateOnly(deal.expected_invoice_date)}</strong>
            </span>
          </div>
          <div style={{ fontSize: 12.5, color: "var(--ink-600)", display: "flex", gap: 16, marginBottom: 16 }}>
            <span>
              Kontakt:{" "}
              <strong>
                {(() => {
                  const contact = companyContacts.find((c) => c.id === deal.contact_id);
                  return contact ? `${contact.first_name} ${contact.last_name}` : "—";
                })()}
              </strong>
            </span>
            <span>
              Vlastník:{" "}
              <strong>
                {users.find((u) => u.id === deal.owner_user_id)?.full_name || "—"}
              </strong>
            </span>
            {deal.sharepoint_folder_url && (
              <span>
                <a href={deal.sharepoint_folder_url} target="_blank" rel="noopener noreferrer">
                  📁 Otevřít složku na SharePointu
                </a>
              </span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span className="badge" style={{ background: STATUS_COLORS[deal.status], fontSize: 13 }}>
            {deal.status}
          </span>
          {!editingDeal && (
            <div style={{ position: "relative" }} ref={actionsMenuRef}>
              <button
                className="btn btn-secondary"
                style={{ padding: "5px 10px", fontSize: 16, lineHeight: 1 }}
                onClick={() => setShowActionsMenu(!showActionsMenu)}
                aria-label="Další akce"
              >
                ⋯
              </button>
              {showActionsMenu && (
                <div
                  style={{
                    position: "absolute",
                    top: "calc(100% + 6px)",
                    right: 0,
                    background: "#fff",
                    border: "1px solid var(--line)",
                    borderRadius: 10,
                    boxShadow: "0 8px 24px rgba(14,12,9,0.15)",
                    minWidth: 200,
                    zIndex: 50,
                    overflow: "hidden",
                  }}
                >
                  <button
                    onClick={() => {
                      startEditDeal();
                      setShowActionsMenu(false);
                    }}
                    style={{
                      display: "block",
                      width: "100%",
                      textAlign: "left",
                      padding: "10px 14px",
                      background: "none",
                      border: "none",
                      fontSize: 13,
                      cursor: "pointer",
                      color: "var(--ink-900)",
                    }}
                  >
                    Upravit
                  </button>
                  {deal.status !== "Ztraceno" && deal.status !== "Fakturováno" && (
                    <button
                      onClick={() => {
                        setShowActionsMenu(false);
                        handleTransition("Ztraceno");
                      }}
                      disabled={transitioning}
                      style={{
                        display: "block",
                        width: "100%",
                        textAlign: "left",
                        padding: "10px 14px",
                        background: "none",
                        border: "none",
                        borderTop: "1px solid var(--paper-200)",
                        fontSize: 13,
                        cursor: "pointer",
                        color: "var(--ink-600)",
                      }}
                    >
                      Označit jako ztracené
                    </button>
                  )}
                  <button
                    onClick={() => {
                      setShowActionsMenu(false);
                      handleDeleteDeal();
                    }}
                    style={{
                      display: "block",
                      width: "100%",
                      textAlign: "left",
                      padding: "10px 14px",
                      background: "none",
                      border: "none",
                      borderTop: "1px solid var(--paper-200)",
                      fontSize: 13,
                      cursor: "pointer",
                      color: "#a13d3d",
                    }}
                  >
                    Smazat
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {editingDeal && (
        <div className="card" style={{ marginBottom: 20 }}>
          <form onSubmit={handleSaveDeal}>
            <div className="field">
              <label>Název případu</label>
              <input
                required
                value={dealEditForm.name}
                onChange={(e) => setDealEditForm({ ...dealEditForm, name: e.target.value })}
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>Odpovědný kontakt</label>
                <select
                  value={dealEditForm.contact_id}
                  onChange={(e) => setDealEditForm({ ...dealEditForm, contact_id: e.target.value })}
                >
                  <option value="">— žádný —</option>
                  {companyContacts.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.first_name} {c.last_name} {c.position ? `(${c.position})` : ""}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Vlastník případu</label>
                <select
                  value={dealEditForm.owner_user_id}
                  onChange={(e) => setDealEditForm({ ...dealEditForm, owner_user_id: e.target.value })}
                >
                  <option value="">— nepřiřazeno —</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>Cena (Kč)</label>
                <input
                  type="number"
                  value={dealEditForm.price}
                  onChange={(e) => setDealEditForm({ ...dealEditForm, price: e.target.value })}
                />
              </div>
              <div className="field">
                <label>
                  <input
                    type="checkbox"
                    checked={dealEditForm.deposit_paid}
                    onChange={(e) => setDealEditForm({ ...dealEditForm, deposit_paid: e.target.checked })}
                    style={{ marginRight: 6 }}
                  />
                  Záloha zaplacena
                </label>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>
                  {CLOSE_DATE_EDITABLE_STATUSES.includes(deal.status) ? "Odhadované uzavření" : "Datum uzavření (skutečné)"}
                </label>
                <input
                  type="date"
                  value={dealEditForm.expected_close_date}
                  onChange={(e) => setDealEditForm({ ...dealEditForm, expected_close_date: e.target.value })}
                  disabled={!CLOSE_DATE_EDITABLE_STATUSES.includes(deal.status)}
                />
                {!CLOSE_DATE_EDITABLE_STATUSES.includes(deal.status) && (
                  <div style={{ fontSize: 11.5, color: "var(--ink-400)", marginTop: 3 }}>
                    Zaznamenáno automaticky při přechodu do stavu Objednávka.
                  </div>
                )}
              </div>
              <div className="field">
                <label>
                  {deal.status === INVOICE_DATE_LOCKED_STATUS ? "Datum fakturace (skutečné)" : "Odhadovaná fakturace"}
                </label>
                <input
                  type="date"
                  value={dealEditForm.expected_invoice_date}
                  onChange={(e) => setDealEditForm({ ...dealEditForm, expected_invoice_date: e.target.value })}
                  disabled={deal.status === INVOICE_DATE_LOCKED_STATUS}
                />
                {deal.status === INVOICE_DATE_LOCKED_STATUS && (
                  <div style={{ fontSize: 11.5, color: "var(--ink-400)", marginTop: 3 }}>
                    Zaznamenáno automaticky při přechodu do stavu Fakturováno.
                  </div>
                )}
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-primary" type="submit">
                Uložit
              </button>
              <button className="btn btn-secondary" type="button" onClick={() => setEditingDeal(false)}>
                Zrušit
              </button>
            </div>
          </form>
        </div>
      )}

      {guidance && (
        <div
          style={{
            background: deal.status === "Ztraceno" ? "var(--paper-100)" : "#fdf3ec",
            border: `1px solid ${deal.status === "Ztraceno" ? "var(--paper-200)" : "var(--ember-500)"}`,
            borderRadius: 12,
            padding: "18px 22px",
            marginBottom: 20,
          }}
        >
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              color: "var(--ember-600, #9c5424)",
              marginBottom: 6,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: STATUS_COLORS[deal.status],
                flexShrink: 0,
              }}
            />
            Co dál
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>{guidance.title}</div>
          <div style={{ fontSize: 13.5, color: "var(--ink-600)", marginBottom: guidance.action ? 14 : 0, lineHeight: 1.5 }}>
            {guidance.description}
          </div>
          {guidance.action && (
            <button className="btn btn-primary" disabled={transitioning} onClick={guidance.action}>
              {guidance.actionLabel}
            </button>
          )}
        </div>
      )}

      {/* --- Kalkulace --- */}
      <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
      <div style={{ flex: "2 1 0%", minWidth: 0 }}>
      <div className="card" style={{ marginBottom: 20 }} id="kalkulace-section">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <div style={{ fontWeight: 600 }}>Kalkulace</div>
          <button className="btn btn-secondary" onClick={() => setShowCalcForm(!showCalcForm)}>
            {showCalcForm ? "Zrušit" : "+ Nová kalkulace"}
          </button>
        </div>

        {showCalcForm && (
          <form
            onSubmit={handleCreateCalculation}
            style={{ marginBottom: 16, paddingBottom: 16, borderBottom: "1px solid var(--paper-200)" }}
          >
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>Produktová řada</label>
                <select
                  value={calcForm.product_line}
                  onChange={(e) => setCalcForm({ ...calcForm, product_line: e.target.value })}
                >
                  <option value="">— vyber —</option>
                  {PRODUCT_LINES.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Dřevina</label>
                <input
                  value={calcForm.wood_species}
                  onChange={(e) => setCalcForm({ ...calcForm, wood_species: e.target.value })}
                  placeholder="např. Modřín"
                />
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>Plocha (m²)</label>
                <input
                  type="number"
                  step="0.01"
                  value={calcForm.area_m2}
                  onChange={(e) => setCalcForm({ ...calcForm, area_m2: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Vzdálenost (km)</label>
                <input
                  type="number"
                  step="0.1"
                  value={calcForm.distance_km}
                  onChange={(e) => setCalcForm({ ...calcForm, distance_km: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Sazba DPH</label>
                <select value={calcForm.vat_rate} onChange={(e) => setCalcForm({ ...calcForm, vat_rate: e.target.value })}>
                  <option value="0.21">21 %</option>
                  <option value="0.12">12 %</option>
                  <option value="0">0 %</option>
                </select>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              <div className="field">
                <label>Sleva na materiál (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={calcForm.discount_material_percent}
                  onChange={(e) => setCalcForm({ ...calcForm, discount_material_percent: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Sleva na montáž (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={calcForm.discount_installation_percent}
                  onChange={(e) => setCalcForm({ ...calcForm, discount_installation_percent: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Výše zálohy (%)</label>
                <input
                  type="number"
                  step="1"
                  value={calcForm.deposit_percent}
                  onChange={(e) => setCalcForm({ ...calcForm, deposit_percent: e.target.value })}
                />
              </div>
            </div>
            <div className="field">
              <label>Platnost nabídky do</label>
              <input
                type="date"
                value={calcForm.valid_until}
                onChange={(e) => setCalcForm({ ...calcForm, valid_until: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Termín realizace</label>
              <input
                value={calcForm.delivery_terms}
                onChange={(e) => setCalcForm({ ...calcForm, delivery_terms: e.target.value })}
                placeholder="např. 6-8 týdnů od objednávky"
              />
            </div>
            <div className="field">
              <label>Platební podmínky</label>
              <input
                value={calcForm.payment_terms}
                onChange={(e) => setCalcForm({ ...calcForm, payment_terms: e.target.value })}
                placeholder="např. Záloha 50 % při objednávce, doplatek při předání díla"
              />
            </div>
            <div style={{ fontSize: 12.5, color: "var(--ink-600)", marginBottom: 12 }}>
              Po uložení přidej jednotlivé položky (materiál, práci, dopravu) - cena se dopočítá
              automaticky z jejich součtu.
            </div>
            <button className="btn btn-primary" type="submit" disabled={calcSaving}>
              {calcSaving ? "Ukládám…" : "Vytvořit kalkulaci"}
            </button>
          </form>
        )}

        {calculations.length === 0 ? (
          <div style={{ fontSize: 13.5, color: "var(--ink-400)" }}>
            Zatím žádná kalkulace - klikni na "+ Nová kalkulace" a začni spočítat cenu.
          </div>
        ) : (
          calculations.map((c) => {
            const items = calcItems[c.id] || [];
            const form = getItemForm(c.id);
            const isExpanded = !!expandedCalcs[c.id];
            return (
              <div
                key={c.id}
                style={{
                  marginBottom: 16,
                  paddingBottom: 16,
                  borderBottom: "1px solid var(--paper-200)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    cursor: "pointer",
                    padding: "6px 0",
                  }}
                  onClick={() => toggleCalcExpanded(c.id)}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span
                      style={{
                        fontSize: 20,
                        color: "var(--ink-600)",
                        width: 22,
                        display: "inline-block",
                        textAlign: "center",
                        lineHeight: 1,
                      }}
                    >
                      {isExpanded ? "▾" : "▸"}
                    </span>
                    <strong style={{ fontSize: 14 }}>
                      {c.product_line || "—"} {c.wood_species ? `/ ${c.wood_species}` : ""}
                    </strong>
                    {c.is_active && <span className="badge" style={{ background: "var(--success)" }}>aktivní</span>}
                  </div>
                  <strong className="mono" style={{ fontSize: 14 }}>{money(c.price_with_vat)}</strong>
                </div>

                {isExpanded && (
                  <div style={{ marginTop: 12 }}>
                    <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
                      {editingCalcId !== c.id && (
                        <button
                          className="btn btn-secondary"
                          style={{ padding: "3px 8px", fontSize: 11.5 }}
                          onClick={() => startEditCalc(c)}
                        >
                          Upravit hlavičku kalkulace
                        </button>
                      )}
                    </div>

                    {editingCalcId === c.id && (
                      <div
                        style={{
                          background: "var(--paper-50)",
                          borderRadius: 8,
                          padding: 14,
                          marginBottom: 14,
                        }}
                      >
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                          <div className="field">
                            <label>Produktová řada</label>
                            <select
                              value={editCalcForm.product_line}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, product_line: e.target.value })}
                            >
                              <option value="">— vyber —</option>
                              {PRODUCT_LINES.map((p) => (
                                <option key={p} value={p}>
                                  {p}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="field">
                            <label>Dřevina</label>
                            <input
                              value={editCalcForm.wood_species}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, wood_species: e.target.value })}
                            />
                          </div>
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                          <div className="field">
                            <label>Plocha (m²)</label>
                            <input
                              type="number"
                              step="0.01"
                              value={editCalcForm.area_m2}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, area_m2: e.target.value })}
                            />
                          </div>
                          <div className="field">
                            <label>Vzdálenost (km)</label>
                            <input
                              type="number"
                              step="0.1"
                              value={editCalcForm.distance_km}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, distance_km: e.target.value })}
                            />
                          </div>
                          <div className="field">
                            <label>Sazba DPH</label>
                            <select
                              value={editCalcForm.vat_rate}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, vat_rate: e.target.value })}
                            >
                              <option value="0.21">21 %</option>
                              <option value="0.12">12 %</option>
                              <option value="0">0 %</option>
                            </select>
                          </div>
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                          <div className="field">
                            <label>Sleva na materiál (%)</label>
                            <input
                              type="number"
                              step="0.1"
                              value={editCalcForm.discount_material_percent}
                              onChange={(e) =>
                                setEditCalcForm({ ...editCalcForm, discount_material_percent: e.target.value })
                              }
                            />
                          </div>
                          <div className="field">
                            <label>Sleva na montáž (%)</label>
                            <input
                              type="number"
                              step="0.1"
                              value={editCalcForm.discount_installation_percent}
                              onChange={(e) =>
                                setEditCalcForm({ ...editCalcForm, discount_installation_percent: e.target.value })
                              }
                            />
                          </div>
                          <div className="field">
                            <label>Výše zálohy (%)</label>
                            <input
                              type="number"
                              step="1"
                              value={editCalcForm.deposit_percent}
                              onChange={(e) => setEditCalcForm({ ...editCalcForm, deposit_percent: e.target.value })}
                            />
                          </div>
                        </div>
                        <div className="field">
                          <label>Platnost nabídky do</label>
                          <input
                            type="date"
                            value={editCalcForm.valid_until}
                            onChange={(e) => setEditCalcForm({ ...editCalcForm, valid_until: e.target.value })}
                          />
                        </div>
                        <div className="field">
                          <label>Termín realizace</label>
                          <input
                            value={editCalcForm.delivery_terms}
                            onChange={(e) => setEditCalcForm({ ...editCalcForm, delivery_terms: e.target.value })}
                          />
                        </div>
                        <div className="field">
                          <label>Platební podmínky</label>
                          <input
                            value={editCalcForm.payment_terms}
                            onChange={(e) => setEditCalcForm({ ...editCalcForm, payment_terms: e.target.value })}
                          />
                        </div>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button
                            className="btn btn-primary"
                            style={{ padding: "6px 14px", fontSize: 13 }}
                            onClick={() => handleSaveCalc(c.id)}
                          >
                            Uložit
                          </button>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: "6px 14px", fontSize: 13 }}
                            onClick={() => setEditingCalcId(null)}
                          >
                            Zrušit
                          </button>
                        </div>
                      </div>
                    )}

                    {(c.discount_material_percent > 0 || c.discount_installation_percent > 0) && (
                      <div style={{ fontSize: 12.5, color: "var(--ink-600)", marginBottom: 8 }}>
                        Sleva materiál: {Number(c.discount_material_percent)} % · Sleva montáž:{" "}
                        {Number(c.discount_installation_percent)} %
                      </div>
                    )}

                    {items.length > 0 && (
                      <table className="table" style={{ marginBottom: 10 }}>
                        <thead>
                          <tr>
                            <th>Kategorie</th>
                            <th>Položka</th>
                            <th>Množství</th>
                            <th>Jedn. cena</th>
                            <th>Celkem</th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>
                          {items.map((it) =>
                            editingItemId === it.id ? (
                              <tr key={it.id}>
                                <td>
                                  <select
                                    value={editItemForm.category}
                                    onChange={(e) => setEditItemForm({ ...editItemForm, category: e.target.value })}
                                    style={{ fontSize: 12.5, padding: "4px 6px" }}
                                  >
                                    {CATEGORIES.map((cat) => (
                                      <option key={cat} value={cat}>
                                        {cat}
                                      </option>
                                    ))}
                                  </select>
                                </td>
                                <td>
                                  <input
                                    value={editItemForm.name}
                                    onChange={(e) => setEditItemForm({ ...editItemForm, name: e.target.value })}
                                    style={{ fontSize: 13, padding: "4px 6px", width: "100%" }}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    step="0.01"
                                    value={editItemForm.quantity}
                                    onChange={(e) => setEditItemForm({ ...editItemForm, quantity: e.target.value })}
                                    style={{ fontSize: 13, padding: "4px 6px", width: 70 }}
                                  />
                                  <input
                                    value={editItemForm.unit}
                                    onChange={(e) => setEditItemForm({ ...editItemForm, unit: e.target.value })}
                                    placeholder="jedn."
                                    style={{ fontSize: 13, padding: "4px 6px", width: 50, marginLeft: 4 }}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    step="0.01"
                                    value={editItemForm.unit_price}
                                    onChange={(e) => setEditItemForm({ ...editItemForm, unit_price: e.target.value })}
                                    style={{ fontSize: 13, padding: "4px 6px", width: 90 }}
                                  />
                                </td>
                                <td className="mono">
                                  {money(Number(editItemForm.quantity || 0) * Number(editItemForm.unit_price || 0))}
                                </td>
                                <td style={{ whiteSpace: "nowrap" }}>
                                  <button
                                    className="btn btn-primary"
                                    style={{ padding: "3px 8px", fontSize: 11.5, marginRight: 4 }}
                                    onClick={() => handleSaveEditItem(c.id, it.id)}
                                  >
                                    Uložit
                                  </button>
                                  <button
                                    className="btn btn-secondary"
                                    style={{ padding: "3px 8px", fontSize: 11.5 }}
                                    onClick={cancelEditItem}
                                  >
                                    Zrušit
                                  </button>
                                </td>
                              </tr>
                            ) : (
                              <tr key={it.id}>
                                <td style={{ fontSize: 12.5, color: "var(--ink-600)" }}>{it.category}</td>
                                <td>{it.name}</td>
                                <td className="mono">
                                  {Number(it.quantity)} {it.unit || ""}
                                </td>
                                <td className="mono">{money(it.unit_price)}</td>
                                <td className="mono">{money(Number(it.quantity) * Number(it.unit_price))}</td>
                                <td style={{ whiteSpace: "nowrap" }}>
                                  <button
                                    className="btn btn-secondary"
                                    style={{ padding: "3px 8px", fontSize: 11.5, marginRight: 4 }}
                                    onClick={() => startEditItem(it)}
                                  >
                                    Upravit
                                  </button>
                                  <button
                                    className="btn btn-danger"
                                    style={{ padding: "3px 8px", fontSize: 11.5 }}
                                    onClick={() => handleDeleteItem(c.id, it.id)}
                                  >
                                    Smazat
                                  </button>
                                </td>
                              </tr>
                            )
                          )}
                        </tbody>
                      </table>
                    )}

                    {form.category === "Materiál" && woodSpeciesList.length > 0 && (
                      <div
                        style={{
                          background: "var(--paper-50)",
                          border: "1px solid var(--paper-200)",
                          borderRadius: 8,
                          padding: "10px 12px",
                          marginBottom: 10,
                        }}
                      >
                        <div className="field" style={{ marginBottom: 0 }}>
                          <label style={{ color: "var(--ember-600)" }}>🪵 Předvyplnit z dřeviny</label>
                          <select
                            onChange={(e) => {
                              if (e.target.value) handleApplyWoodSpecies(c.id, e.target.value, c.product_line, c.area_m2);
                              e.target.value = "";
                            }}
                            defaultValue=""
                          >
                            <option value="" disabled>
                              — vyber dřevinu —
                            </option>
                            {woodSpeciesList.map((s) => (
                              <option key={s.id} value={s.id}>
                                {s.name}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    )}
                    {form.category === "Doprava" && (
                      <div style={{ marginBottom: 8 }}>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: "4px 10px", fontSize: 12.5 }}
                          onClick={() => handleCalculateTransport(c.id, c.distance_km)}
                        >
                          Vypočítat dle vzdálenosti ({c.distance_km ? `${Number(c.distance_km)} km` : "vzdálenost nezadána"})
                        </button>
                      </div>
                    )}

                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "110px 1.5fr 80px 90px 100px auto",
                        gap: 6,
                        alignItems: "end",
                        marginBottom: 10,
                      }}
                    >
                      <div className="field" style={{ marginBottom: 0 }}>
                        <label>Kategorie</label>
                        <select
                          value={form.category}
                          onChange={(e) => handleCategoryChange(c.id, e.target.value, c)}
                        >
                          {CATEGORIES.map((cat) => (
                            <option key={cat} value={cat}>
                              {cat}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="field" style={{ marginBottom: 0 }}>
                        <label>Název položky</label>
                        <input value={form.name} onChange={(e) => setItemForm(c.id, { name: e.target.value })} />
                      </div>
                      <div className="field" style={{ marginBottom: 0 }}>
                        <label>Jednotka</label>
                        <input
                          value={form.unit}
                          onChange={(e) => setItemForm(c.id, { unit: e.target.value })}
                          placeholder="m²"
                        />
                      </div>
                      <div className="field" style={{ marginBottom: 0 }}>
                        <label>Množství</label>
                        <input
                          type="number"
                          step="0.01"
                          value={form.quantity}
                          onChange={(e) => setItemForm(c.id, { quantity: e.target.value })}
                        />
                      </div>
                      <div className="field" style={{ marginBottom: 0 }}>
                        <label>Jedn. cena</label>
                        <input
                          type="number"
                          step="0.01"
                          value={form.unit_price}
                          onChange={(e) => setItemForm(c.id, { unit_price: e.target.value })}
                        />
                      </div>
                      <button
                        className="btn"
                        style={{ background: "var(--success)", color: "#fff", border: "none" }}
                        onClick={() => handleAddItem(c.id)}
                      >
                        + Přidat
                      </button>
                    </div>

                    <div
                      style={{
                        display: "flex",
                        justifyContent: "flex-end",
                        gap: 20,
                        fontSize: 13.5,
                        paddingTop: 8,
                        borderTop: "1px solid var(--paper-200)",
                      }}
                    >
                      <div>
                        Bez DPH: <strong className="mono">{money(c.price_without_vat)}</strong>
                      </div>
                      <div>
                        DPH: <strong className="mono">{money(c.vat_amount)}</strong>
                      </div>
                      <div>
                        Celkem: <strong className="mono">{money(c.price_with_vat)}</strong>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* --- Dokumenty --- */}
      <div className="card" id="dokumenty-section" style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <div style={{ fontWeight: 600 }}>Dokumenty</div>
          <button
            className="btn btn-secondary"
            style={{ padding: "4px 10px", fontSize: 12.5 }}
            onClick={handleCreateNewOfferVersion}
          >
            + Nová verze nabídky
          </button>
        </div>
        {documents.length === 0 ? (
          <div style={{ fontSize: 13.5, color: "var(--ink-400)" }}>Zatím žádné dokumenty</div>
        ) : (
          documents.map((d) => {
            const views = documentViews[d.id];
            const viewCount = views ? views.length : null;

            const isLatestOfType =
              d.version ===
              Math.max(...documents.filter((x) => x.document_type === d.document_type).map((x) => x.version));

            return (
              <div
                key={d.id}
                style={{
                  fontSize: 13.5,
                  marginBottom: 10,
                  paddingBottom: 10,
                  borderBottom: "1px solid var(--paper-200)",
                }}
              >
                <div>
                  <strong>{d.document_type}</strong> (v{d.version})
                  {isLatestOfType && (
                    <span
                      className="badge"
                      style={{ background: "var(--success)", marginLeft: 8, fontSize: 10.5 }}
                    >
                      Aktuální
                    </span>
                  )}
                  {d.document_type === "Objednávka" && (
                    <span
                      className="badge"
                      style={{
                        background: d.confirmed_at ? "var(--success)" : "#c1863f",
                        marginLeft: 6,
                        fontSize: 10.5,
                      }}
                    >
                      {d.confirmed_at ? "Potvrzená" : "Nepotvrzená"}
                    </span>
                  )}
                </div>
                {d.document_type === "Objednávka" && d.confirmed_at && (
                  <div style={{ fontSize: 11.5, color: "var(--ink-600)", marginTop: 2 }}>
                    Potvrdil(a) {d.confirmed_by_name} dne {formatDate(d.confirmed_at)}
                  </div>
                )}
                <div style={{ color: "var(--ink-600)", marginBottom: 6 }}>Vytvořeno: {formatDate(d.created_at)}</div>
                {d.document_type === "Dodací list" && d.delivery_note_filename && (
                  <div style={{ marginBottom: 6 }}>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: "4px 10px", fontSize: 12 }}
                      onClick={() => handleDownloadDeliveryNote(d.id)}
                    >
                      Stáhnout dodací list (PDF)
                    </button>
                  </div>
                )}
                {(d.document_type === "Zálohová faktura" || d.document_type === "Finální faktura") &&
                  d.amount != null && (
                    <div style={{ marginBottom: 6 }}>
                      Částka: <strong className="mono">{money(d.amount)}</strong>
                      {d.idoklad_invoice_number && (
                        <>
                          {" · "}
                          iDoklad č. <strong>{d.idoklad_invoice_number}</strong>
                          {d.idoklad_pdf_url && (
                            <>
                              {" "}
                              <a href={d.idoklad_pdf_url} target="_blank" rel="noopener noreferrer">
                                (PDF)
                              </a>
                            </>
                          )}
                        </>
                      )}
                    </div>
                  )}

                {(d.document_type === "Zálohová faktura" || d.document_type === "Finální faktura") && (
                  <div style={{ marginBottom: 6 }}>
                    {d.suggested_invoice_line && (
                      <div
                        style={{
                          background: "var(--paper-50)",
                          border: "1px solid var(--paper-200)",
                          borderRadius: 8,
                          padding: "10px 12px",
                          marginBottom: 8,
                        }}
                      >
                        <div style={{ fontSize: 11, color: "var(--ink-400)", marginBottom: 4 }}>
                          Návrh položky faktury (kvůli 12% DPH musí být jen jedna položka):
                        </div>
                        <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                          <div style={{ fontSize: 12.5, color: "var(--ink-900)", flex: 1 }}>
                            {d.suggested_invoice_line}
                          </div>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: "3px 8px", fontSize: 11.5, flexShrink: 0 }}
                            onClick={() => {
                              navigator.clipboard.writeText(d.suggested_invoice_line);
                              setCopiedInvoiceLineId(d.id);
                              setTimeout(() => setCopiedInvoiceLineId(null), 2000);
                            }}
                          >
                            {copiedInvoiceLineId === d.id ? "Zkopírováno ✓" : "Zkopírovat"}
                          </button>
                        </div>
                      </div>
                    )}
                    {!d.invoice_pdf_filename ? (
                      <div
                        style={{
                          background: "#fdf3ec",
                          border: "1px solid var(--ember-500)",
                          borderRadius: 10,
                          padding: "12px 14px",
                          marginTop: 4,
                        }}
                      >
                        <div style={{ fontSize: 12.5, color: "var(--ink-600)", marginBottom: 8 }}>
                          Vystav prosím {d.document_type.toLowerCase()} (např. v iDokladu) a nahraj ji sem jako PDF.
                        </div>
                        <input
                          type="file"
                          accept="application/pdf"
                          id={`invoice-upload-${d.id}`}
                          style={{ display: "none" }}
                          onChange={(e) => handleUploadInvoice(d.id, e.target.files[0])}
                        />
                        <label
                          htmlFor={`invoice-upload-${d.id}`}
                          className="btn btn-primary"
                          style={{ padding: "8px 16px", fontSize: 13, cursor: "pointer", display: "inline-block" }}
                        >
                          {uploadingInvoiceId === d.id ? "Nahrávám…" : "📎 Nahrát fakturu (PDF)"}
                        </label>
                      </div>
                    ) : (
                      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: "5px 10px", fontSize: 12.5 }}
                          onClick={() => handleDownloadInvoice(d.id)}
                        >
                          Stáhnout fakturu
                        </button>
                        {!d.invoice_sent_at ? (
                          <button
                            className="btn btn-primary"
                            style={{ padding: "5px 10px", fontSize: 12.5 }}
                            onClick={() => handleSendInvoiceEmail(d.id)}
                            disabled={sendingInvoiceId === d.id}
                          >
                            {sendingInvoiceId === d.id ? "Odesílám…" : "Odeslat zákazníkovi"}
                          </button>
                        ) : (
                          <span style={{ fontSize: 12, color: "var(--ink-600)" }}>
                            ✓ Odesláno {formatDate(d.invoice_sent_at)}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {(d.document_type === "Nabídka" || d.document_type === "Objednávka") && (
                  <>
                    <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: "5px 10px", fontSize: 12.5 }}
                        onClick={() => handleCopyLink(d.access_token, d.id)}
                      >
                        {copiedDoc === d.id ? "Zkopírováno ✓" : "Zkopírovat veřejný odkaz"}
                      </button>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: "5px 10px", fontSize: 12.5 }}
                        onClick={() => handleToggleViews(d.id)}
                      >
                        {expandedDoc === d.id ? "Skrýt zobrazení" : "Zobrazit sledování"}
                      </button>
                    </div>

                    {expandedDoc === d.id && (
                      <div
                        style={{
                          background: "var(--paper-50)",
                          borderRadius: 6,
                          padding: "10px 12px",
                          marginTop: 4,
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                          <div style={{ fontWeight: 600 }}>{views ? `Otevřeno ${viewCount}×` : "Sledování"}</div>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: "3px 8px", fontSize: 11.5 }}
                            onClick={() => refreshViews(d.id)}
                          >
                            Obnovit
                          </button>
                        </div>
                        {!views ? (
                          <div style={{ color: "var(--ink-400)" }}>Načítám…</div>
                        ) : views.length === 0 ? (
                          <div style={{ color: "var(--ink-400)" }}>Nabídka zatím nebyla otevřena.</div>
                        ) : (
                          views.map((v) => (
                            <div key={v.id} style={{ color: "var(--ink-600)", marginBottom: 3 }}>
                              {formatDate(v.viewed_at)}
                              {v.duration_seconds != null ? ` · prohlíženo ${v.duration_seconds} s` : " · doba čtení neznámá"}
                            </div>
                          ))
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          })
        )}
      </div>
      </div>

      <div style={{ flex: "1 1 0%", minWidth: 280 }}>
      {/* --- Poznámky --- */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ fontWeight: 600, marginBottom: 10 }}>Poznámky</div>
        <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
          <input
            type="text"
            placeholder="Přidat poznámku…"
            value={newNoteText}
            onChange={(e) => setNewNoteText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAddNote();
            }}
            style={{ flex: 1, padding: "8px 12px", fontSize: 13, borderRadius: 8, border: "1px solid var(--paper-200)" }}
          />
          <button className="btn btn-primary" onClick={handleAddNote} disabled={addingNote || !newNoteText.trim()}>
            {addingNote ? "Přidávám…" : "Přidat"}
          </button>
        </div>
        {notes.length === 0 ? (
          <div style={{ fontSize: 13, color: "var(--ink-400)" }}>Zatím žádné poznámky</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: 320, overflowY: "auto" }}>
            {notes.map((n) => (
              <div key={n.id} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <div style={{ flexShrink: 0, width: 3, height: 3, borderRadius: "50%", background: "var(--ink-400)", marginTop: 8 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, color: "var(--ink-900)", lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                    {n.content}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--ink-400)", marginTop: 2 }}>
                    {n.author_name || "—"} · {formatDate(n.created_at)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      {/* --- Poptávka / Dokumentace (volitelné, sbalené) --- */}
      <div className="card">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            cursor: "pointer",
            marginBottom: showAttachments ? 10 : 0,
          }}
          onClick={() => setShowAttachments(!showAttachments)}
        >
          <div style={{ fontWeight: 600, color: "var(--ink-600)" }}>
            {showAttachments ? "▾" : "▸"} Poptávka / Dokumentace
            {attachments.length > 0 && (
              <span style={{ fontWeight: 400, color: "var(--ink-400)" }}> ({attachments.length})</span>
            )}
          </div>
          {showAttachments && (
            <div onClick={(e) => e.stopPropagation()}>
              <input
                type="file"
                id="attachment-upload"
                style={{ display: "none" }}
                onChange={(e) => {
                  if (e.target.files[0]) handleUploadAttachment(e.target.files[0]);
                  e.target.value = "";
                }}
              />
              <label
                htmlFor="attachment-upload"
                className="btn btn-secondary"
                style={{ padding: "4px 10px", fontSize: 12.5, cursor: "pointer", display: "inline-block" }}
              >
                {uploadingAttachment ? "Nahrávám…" : "+ Nahrát soubor (výkres, dokumentace)"}
              </label>
            </div>
          )}
        </div>
        {showAttachments &&
          (attachments.length === 0 ? (
            <div style={{ fontSize: 13, color: "var(--ink-400)" }}>Zatím žádné přílohy</div>
          ) : (
            attachments.map((a) => (
              <div
                key={a.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 0",
                  borderBottom: "1px solid var(--paper-200)",
                  fontSize: 13,
                }}
              >
                <span>{a.original_filename}</span>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <span style={{ fontSize: 11.5, color: "var(--ink-400)" }}>{formatDate(a.uploaded_at)}</span>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: "3px 8px", fontSize: 11.5 }}
                    onClick={() => handleDownloadAttachment(a.id, a.original_filename)}
                  >
                    Stáhnout
                  </button>
                  <button
                    className="btn btn-danger"
                    style={{ padding: "3px 8px", fontSize: 11.5 }}
                    onClick={() => handleDeleteAttachment(a.id)}
                  >
                    Smazat
                  </button>
                </div>
              </div>
            ))
          ))}
      </div>
      </div>
      </div>
    </ProtectedShell>
  );
}
