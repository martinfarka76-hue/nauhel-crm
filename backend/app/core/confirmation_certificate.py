"""
Generování "Potvrzení objednávky" certifikátu (PDF) - důkazní záznam pro
případ sporu/soudního řešení. Obsahuje jméno a čas potvrzení, IP adresu,
otisk (hash) znění VOP v době potvrzení, a odkaz na potvrzený dokument.
Nahrává se do SharePoint podsložky "06_Smlouvy a specifikace".
"""
import logging
from datetime import datetime

from weasyprint import HTML

from app.core.branding import LOGO_DATA_URI_BLACK
from app.models.document import Document
from app.models.deal import Deal
from app.models.company import Company

logger = logging.getLogger("nauhel_crm.confirmation_certificate")


def generate_confirmation_certificate_pdf(document: Document, deal: Deal, company: Company | None) -> bytes:
    confirmed_str = document.confirmed_at.strftime("%d.%m.%Y %H:%M:%S") if document.confirmed_at else "—"
    generated_str = datetime.utcnow().strftime("%d.%m.%Y %H:%M:%S")

    html_content = f"""
    <html>
    <head>
    <style>
        body {{ font-family: 'DejaVu Sans', sans-serif; color: #211d17; padding: 40px; }}
        .logo {{ height: 32px; margin-bottom: 24px; }}
        h1 {{ font-size: 20px; color: #211d17; margin-bottom: 4px; }}
        .subtitle {{ color: #5c564a; font-size: 13px; margin-bottom: 28px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        td {{ padding: 8px 0; border-bottom: 1px solid #ded8ca; font-size: 13px; vertical-align: top; }}
        td.label {{ color: #5c564a; width: 220px; }}
        td.value {{ font-weight: 600; }}
        .footer {{ margin-top: 40px; font-size: 10.5px; color: #8a8578; }}
        .mono {{ font-family: 'DejaVu Sans Mono', monospace; font-size: 11.5px; word-break: break-all; }}
    </style>
    </head>
    <body>
        <img class="logo" src="{LOGO_DATA_URI_BLACK}" />
        <h1>Potvrzení objednávky - záznam pro důkazní účely</h1>
        <div class="subtitle">
            Automaticky generovaný záznam o elektronickém potvrzení objednávky/nabídky
            zákazníkem přes veřejný odkaz.
        </div>
        <table>
            <tr><td class="label">Obchodní případ</td><td class="value">{deal.name}</td></tr>
            <tr><td class="label">Firma</td><td class="value">{company.name if company else "—"}</td></tr>
            <tr><td class="label">IČO</td><td class="value">{company.ico if company and company.ico else "—"}</td></tr>
            <tr><td class="label">Typ dokumentu</td><td class="value">{document.document_type.value} (verze {document.version})</td></tr>
            <tr><td class="label">Potvrdil(a)</td><td class="value">{document.confirmed_by_name or "—"}</td></tr>
            <tr><td class="label">Datum a čas potvrzení</td><td class="value">{confirmed_str}</td></tr>
            <tr><td class="label">IP adresa při potvrzení</td><td class="value mono">{document.confirmation_ip_address or "—"}</td></tr>
            <tr><td class="label">Souhlas s VOP</td><td class="value">{"Ano" if document.agreed_to_terms else "Ne"}</td></tr>
            <tr><td class="label">Otisk (SHA-256) znění VOP v době potvrzení</td><td class="value mono">{document.vop_snapshot_sha256 or "—"}</td></tr>
            <tr><td class="label">ID dokumentu v systému</td><td class="value mono">{document.id}</td></tr>
        </table>
        <div class="footer">
            Vygenerováno automaticky systémem NAUHEL CRM dne {generated_str} UTC. Jde o vlastní "domácí"
            náhradu elektronického podpisu, ne o kvalifikovaný elektronický podpis ve smyslu nařízení eIDAS.
        </div>
    </body>
    </html>
    """
    return HTML(string=html_content).write_pdf()
