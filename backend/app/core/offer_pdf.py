"""
Generování PDF verze nabídky/objednávky (pro archivaci na SharePointu) -
HTML šablona podobná veřejné webové stránce, převedená přes WeasyPrint.
"""
import logging
from decimal import Decimal

from weasyprint import HTML

from app.models.document import Document
from app.models.deal import Deal
from app.models.company import Company
from app.models.calculation import Calculation
from app.models.calculation_item import CalculationItem

logger = logging.getLogger("nauhel_crm.offer_pdf")


def _money(value) -> str:
    if value is None:
        return "—"
    return f"{Decimal(value):,.0f} Kč".replace(",", " ")


def generate_offer_pdf(document: Document, deal: Deal, company: Company, calc: Calculation | None, items: list) -> bytes:
    """Vygeneruje PDF bajty pro danou Nabídku/Objednávku."""
    items_rows = ""
    if calc and items:
        for item in items:
            line_total = Decimal(item.quantity) * Decimal(item.unit_price)
            items_rows += f"""
            <tr>
              <td>{item.name}</td>
              <td style="text-align:right">{item.quantity} {item.unit or ''}</td>
              <td style="text-align:right">{_money(item.unit_price)}</td>
              <td style="text-align:right">{_money(line_total)}</td>
            </tr>
            """

    stats_html = ""
    if calc:
        if calc.product_line:
            stats_html += f'<div class="stat"><div class="label">Produktová řada</div><div class="value">{calc.product_line}</div></div>'
        if calc.wood_species:
            stats_html += f'<div class="stat"><div class="label">Dřevina</div><div class="value">{calc.wood_species}</div></div>'
        if calc.area_m2:
            stats_html += f'<div class="stat"><div class="label">Plocha fasády</div><div class="value">{calc.area_m2} m²</div></div>'

    totals_html = ""
    if calc:
        totals_html = f"""
        <div class="totals">
          <div class="row"><span>Mezisoučet bez DPH</span><span>{_money(calc.price_without_vat)}</span></div>
          <div class="row"><span>DPH</span><span>{_money(calc.vat_amount)}</span></div>
          <div class="row total"><span>Celkem s DPH</span><span>{_money(calc.price_with_vat)}</span></div>
        </div>
        """

    html_content = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      body {{ font-family: 'DejaVu Sans', sans-serif; color: #17140f; margin: 40px; }}
      .eyebrow {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #8a8578; }}
      h1 {{ font-size: 22px; margin: 4px 0 16px; }}
      .stats {{ display: flex; border: 1px solid #e6e1d7; border-radius: 8px; margin-bottom: 16px; }}
      .stat {{ flex: 1; padding: 10px 14px; border-right: 1px solid #e6e1d7; }}
      .stat:last-child {{ border-right: none; }}
      .stat .label {{ font-size: 10px; text-transform: uppercase; color: #8a8578; }}
      .stat .value {{ font-size: 14px; font-weight: 700; }}
      table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
      th {{ text-align: left; font-size: 11px; color: #8a8578; border-bottom: 1px solid #e6e1d7; padding: 6px 0; }}
      td {{ font-size: 13px; padding: 8px 0; border-bottom: 1px solid #f2efe9; }}
      .totals .row {{ display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; }}
      .totals .total {{ font-weight: 700; font-size: 16px; border-top: 1px solid #17140f; padding-top: 10px; }}
      .footer {{ margin-top: 30px; font-size: 11px; color: #8a8578; }}
    </style>
    </head>
    <body>
      <div class="eyebrow">{document.document_type.value} pro {company.name}</div>
      <h1>{deal.name}</h1>
      <div class="stats">{stats_html}</div>
      <table>
        <thead><tr><th>Položka</th><th style="text-align:right">Množství</th><th style="text-align:right">Jedn. cena</th><th style="text-align:right">Celkem</th></tr></thead>
        <tbody>{items_rows}</tbody>
      </table>
      {totals_html}
      <div class="footer">
        NAUHEL s.r.o. · Ve Mlejnku 108, 257 65 Čechtice · telefon: 605 457 927<br>
        IČO: 24463973 · DIČ: CZ24463973
      </div>
    </body>
    </html>
    """

    return HTML(string=html_content).write_pdf()
