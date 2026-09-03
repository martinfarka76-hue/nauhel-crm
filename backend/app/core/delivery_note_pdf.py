"""
Generování Dodacího listu jako PDF (WeasyPrint, stejný vizuální styl jako
u PDF nabídek/objednávek - viz offer_pdf.py) - vzniká automaticky při
přechodu Dealu na stav "Vyrobeno".

Část dokumentu (stav dodávky, stav zboží při převzetí, podpisy) se
vyplňuje ručně při fyzickém předání - necháváme prázdné/nezaškrtnuté,
kromě "Kompletní dodávka", která je předzaškrtnutá.
"""
import logging
from datetime import date

from weasyprint import HTML
from sqlalchemy.orm import Session

from app.models.deal import Deal
from app.models.company import Company
from app.models.contact import Contact
from app.models.user import User
from app.models.calculation import Calculation
from app.models.calculation_item import CalculationItem
from app.models.enums import ItemCategory

logger = logging.getLogger("nauhel_crm.delivery_note_pdf")


def generate_delivery_note_pdf(
    db: Session, deal: Deal, company: Company | None, contact: Contact | None, owner: User | None
) -> bytes:
    """Vygeneruje PDF bajty dodacího listu."""
    cislo = ""
    if deal.sharepoint_folder_year and deal.sharepoint_folder_number:
        cislo = f"{deal.sharepoint_folder_year}_{deal.sharepoint_folder_number:03d}"

    calc = db.query(Calculation).filter(Calculation.deal_id == deal.id, Calculation.is_active.is_(True)).first()
    material_items = []
    if calc:
        items = (
            db.query(CalculationItem)
            .filter(CalculationItem.calculation_id == calc.id)
            .order_by(CalculationItem.display_order)
            .all()
        )
        material_items = [i for i in items if i.category == ItemCategory.MATERIAL]

    items_rows = ""
    for idx, item in enumerate(material_items, start=1):
        items_rows += f"""
        <tr>
          <td>{idx}</td>
          <td>{item.name}</td>
          <td style="text-align:right">{item.quantity} {item.unit or ''}</td>
          <td></td>
        </tr>
        """
    if not items_rows:
        items_rows = '<tr><td colspan="4" style="color:#8a8578">Žádné materiálové položky v aktivní kalkulaci</td></tr>'

    ico_dic = ""
    if company:
        ico_dic = f"{company.ico or ''} / {company.dic or ''}".strip(" /")

    html_content = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      body {{ font-family: 'DejaVu Sans', sans-serif; color: #17140f; margin: 40px; font-size: 12.5px; }}
      .header {{ display: flex; justify-content: space-between; margin-bottom: 24px; }}
      .company-info {{ font-size: 11px; color: #8a8578; line-height: 1.5; }}
      .company-name {{ font-size: 16px; font-weight: 700; color: #17140f; margin-bottom: 4px; }}
      .doc-title {{ font-size: 18px; font-weight: 700; color: #b5652d; text-align: right; margin-bottom: 8px; }}
      .meta-table {{ border-collapse: collapse; }}
      .meta-table td {{ padding: 4px 10px; font-size: 11px; border: 1px solid #e6e1d7; }}
      .meta-table td.label {{ color: #8a8578; background: #faf8f5; text-align: right; }}
      .meta-table td.value {{ font-weight: 600; }}
      .section-title {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
                          color: #8a8578; margin: 20px 0 8px; }}
      .two-col {{ display: flex; gap: 20px; }}
      .info-box {{ flex: 1; border: 1px solid #e6e1d7; border-radius: 8px; padding: 10px 14px; }}
      .info-row {{ display: flex; justify-content: space-between; font-size: 11.5px; padding: 3px 0;
                    border-bottom: 1px solid #f2efe9; }}
      .info-row:last-child {{ border-bottom: none; }}
      .info-row .k {{ color: #8a8578; }}
      table.spec {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
      table.spec th {{ text-align: left; font-size: 10.5px; color: #8a8578; text-transform: uppercase;
                        border-bottom: 1px solid #e6e1d7; padding: 6px 4px; }}
      table.spec td {{ font-size: 12px; padding: 7px 4px; border-bottom: 1px solid #f2efe9; }}
      .status-box {{ border: 1px solid #e6e1d7; border-radius: 8px; padding: 12px 16px; margin-top: 6px; }}
      .checkbox-row {{ font-size: 12px; margin-bottom: 6px; }}
      .checkbox-row .checked {{ color: #b5652d; font-weight: 700; }}
      .legal-note {{ font-size: 10px; color: #8a8578; margin-top: 16px; line-height: 1.5; }}
      .signatures {{ display: flex; gap: 40px; margin-top: 30px; }}
      .signature-col {{ flex: 1; font-size: 11px; }}
      .signature-col .title {{ font-weight: 700; margin-bottom: 16px; }}
      .signature-line {{ border-bottom: 1px solid #17140f; margin: 24px 0 4px; }}
    </style>
    </head>
    <body>
      <div class="header">
        <div>
          <div class="company-name">NAUHEL s.r.o.</div>
          <div class="company-info">
            Ve Mlejnku 108, 257 65 Čechtice<br>
            IČO: 24463973<br>
            info@nauhel.cz · +420 605 457 927 · www.nauhel.cz
          </div>
        </div>
        <div>
          <div class="doc-title">DODACÍ LIST</div>
          <table class="meta-table">
            <tr><td class="label">Č. dodacího listu</td><td class="value">{cislo}</td></tr>
            <tr><td class="label">Datum expedice</td><td class="value">{date.today().strftime("%d.%m.%Y")}</td></tr>
            <tr><td class="label">K objednávce č.</td><td class="value">{cislo}</td></tr>
            <tr><td class="label">Vystavil</td><td class="value">{owner.full_name if owner else ""}</td></tr>
          </table>
        </div>
      </div>

      <div class="two-col">
        <div class="info-box">
          <div class="section-title" style="margin-top:0">Příjemce</div>
          <div class="info-row"><span class="k">Firma / Jméno</span><span>{company.name if company else ""}</span></div>
          <div class="info-row"><span class="k">IČO / DIČ</span><span>{ico_dic}</span></div>
          <div class="info-row"><span class="k">Fakturační adresa</span><span>{company.address if company else ""}</span></div>
          <div class="info-row"><span class="k">Kontaktní osoba</span><span>{f"{contact.first_name} {contact.last_name}" if contact else ""}</span></div>
        </div>
        <div class="info-box">
          <div class="section-title" style="margin-top:0">Dodací adresa</div>
          <div class="info-row"><span class="k">Firma / Jméno</span><span>{company.name if company else ""}</span></div>
          <div class="info-row"><span class="k">Adresa</span><span>{company.address if company else ""}</span></div>
          <div class="info-row"><span class="k">Telefon</span><span>{contact.phone if contact else ""}</span></div>
        </div>
      </div>

      <div class="section-title">Specifikace dodávaného zboží</div>
      <table class="spec">
        <thead><tr><th>#</th><th>Popis - produkt, dřevina, profil</th><th style="text-align:right">Množství</th><th>Poznámka</th></tr></thead>
        <tbody>{items_rows}</tbody>
      </table>

      <div class="section-title">Stav dodávky</div>
      <div class="status-box">
        <div class="checkbox-row"><span class="checked">☒</span> <strong>Kompletní dodávka</strong> - veškerý materiál dle objednávky dodán</div>
        <div class="checkbox-row">☐ <strong>Částečná dodávka</strong> - zbývá dodat: ___________________________</div>
      </div>

      <div class="section-title">Stav zboží při převzetí</div>
      <div class="status-box">
        <div class="checkbox-row">☐ Zboží převzato bez závad - množství a viditelný stav odpovídá dodacímu listu.</div>
        <div class="checkbox-row">☐ Zboží převzato s výhradami (popište níže):</div>
        <div style="border-bottom: 1px solid #e6e1d7; height: 30px; margin-top: 8px;"></div>
      </div>

      <div class="legal-note">
        Příjemce je povinen zkontrolovat množství a viditelný stav zboží při převzetí. Případné závady nebo
        nesoulad je povinen vyznačit do tohoto dodacího listu a neprodleně informovat NAUHEL s.r.o. Vlastnické
        právo k zboží přechází na příjemce až úplným uhrazením kupní ceny (výhrada vlastnictví dle VOP).
      </div>

      <div class="signatures">
        <div class="signature-col">
          <div class="title">Předal - za NAUHEL s.r.o.</div>
          Jméno:
          <div class="signature-line"></div>
          Podpis:
          <div class="signature-line"></div>
          Datum a čas předání:
          <div class="signature-line"></div>
        </div>
        <div class="signature-col">
          <div class="title">Převzal - zákazník</div>
          Jméno:
          <div class="signature-line"></div>
          Podpis (+ razítko u firem):
          <div class="signature-line"></div>
          Datum a čas převzetí:
          <div class="signature-line"></div>
        </div>
      </div>
    </body>
    </html>
    """

    return HTML(string=html_content).write_pdf()
