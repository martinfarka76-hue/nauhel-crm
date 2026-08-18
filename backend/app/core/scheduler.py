"""
Naplánovaná úloha: kontrola nabídek (Document typu Nabídka), které jsou
starší než 7 dní, Deal je stále ve stavu 'Nabídka' (nepotvrzeno), a
reminder ještě nebyl odeslán. Zatím jen loguje - skutečné odeslání emailu
přijde s Microsoft Graph/Outlook integrací.
"""
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.document import Document
from app.models.deal import Deal
from app.models.enums import DealStatus, DocumentType

logger = logging.getLogger("nauhel_crm.reminders")

REMINDER_AFTER_DAYS = 7


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
    scheduler.start()
    logger.info("Scheduler spuštěn - kontrola nepotvrzených nabídek denně v 8:00")
    return scheduler
