"""
Naplánovaná úloha: kontrola nabídek (Document typu Nabídka), které jsou
starší než 7 dní, Deal je stále ve stavu 'Nabídka' (nepotvrzeno), a
reminder ještě nebyl odeslán. Zatím jen loguje - skutečné odeslání emailu
přijde s Microsoft Graph/Outlook integrací.
"""
import logging
from datetime import datetime, timedelta, date

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.document import Document
from app.models.deal import Deal
from app.models.notification import Notification
from app.models.enums import DealStatus, DocumentType

logger = logging.getLogger("nauhel_crm.reminders")

REMINDER_AFTER_DAYS = 7

TERMINAL_STATUSES = [DealStatus.FAKTUROVANO, DealStatus.ZTRACENO]


def check_upcoming_followups() -> None:
    """
    Denní kontrola termínů dalšího kontaktu (next_contact_date) u Dealů.
    Pokud je termín dnes nebo v minulosti, Deal není v koncovém stavu
    (Fakturováno/Ztraceno), a notifikace pro tenhle termín ještě nebyla
    vytvořena (next_contact_notified_at je NULL), vytvoří se notifikace
    a nastaví se příznak - ať se stejná věc nepřipomíná znovu každý den.
    """
    db: Session = SessionLocal()
    try:
        today = date.today()
        candidates = (
            db.query(Deal)
            .filter(
                Deal.next_contact_date.isnot(None),
                Deal.next_contact_date <= today,
                Deal.next_contact_notified_at.is_(None),
                Deal.status.notin_(TERMINAL_STATUSES),
            )
            .all()
        )

        for deal in candidates:
            overdue_days = (today - deal.next_contact_date).days
            if overdue_days > 0:
                message = f"Follow-up: \"{deal.name}\" - termín kontaktu byl {deal.next_contact_date.strftime('%d.%m.%Y')} ({overdue_days} dní po termínu)"
            else:
                message = f"Follow-up: \"{deal.name}\" - dnes je naplánovaný kontakt"

            notification = Notification(
                notification_type="followup_due",
                message=message,
                deal_id=deal.id,
            )
            db.add(notification)
            deal.next_contact_notified_at = datetime.utcnow()
            logger.info("Follow-up notifikace vytvořena pro Deal %s (%s)", deal.id, deal.name)

        if candidates:
            db.commit()
    finally:
        db.close()


def check_unconfirmed_offers() -> None:
    db: Session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=REMINDER_AFTER_DAYS)

        candidates = (
            db.query(Document)
            .join(Deal, Document.deal_id == Deal.id)
            .filter(
                Document.document_type == DocumentType.NABIDKA,
                Document.reminder_sent_at.is_(None),
                Document.created_at <= cutoff,
                Deal.status == DealStatus.NABIDKA,
            )
            .all()
        )

        for document in candidates:
            # TODO: až bude hotová emailová integrace (MS Graph/Outlook),
            # sem přijde reálné odeslání emailu na kontakt u Dealu.
            logger.info(
                "Reminder: Nabídka %s (Deal %s) je %s dní bez potvrzení - "
                "email zatím neodesílán, pouze zaznamenáno.",
                document.id,
                document.deal_id,
                REMINDER_AFTER_DAYS,
            )
            document.reminder_sent_at = datetime.utcnow()

        if candidates:
            db.commit()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Europe/Prague")
    # Kontrola jednou denně v 8:00 - dost pro reminder na 7denní lhůtu
    scheduler.add_job(check_unconfirmed_offers, "cron", hour=8, minute=0, id="unconfirmed_offers_reminder")
    scheduler.add_job(check_upcoming_followups, "cron", hour=8, minute=5, id="followup_reminder")
    scheduler.start()
    logger.info("Scheduler spuštěn - kontrola nepotvrzených nabídek a follow-up termínů denně v 8:00")
    return scheduler
