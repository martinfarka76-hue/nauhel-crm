import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deal_transitions import perform_esignature_confirmation
from app.models.deal import Deal
from app.schemas.deal import DealOut

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

WEBHOOK_SECRET = os.getenv("ESIGNATURE_WEBHOOK_SECRET")


def verify_webhook_secret(x_webhook_secret: str = Header(...)):
    if not WEBHOOK_SECRET or x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Neplatný webhook secret")


@router.post("/esignature/{deal_id}", response_model=DealOut)
def esignature_webhook(
    deal_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: None = Depends(verify_webhook_secret),
):
    """
    Obecný webhook pro potvrzení e-signature (konkrétní nástroj zatím
    nevybrán - endpoint je připraven, autentizace přes sdílený tajný
    klíč v hlavičce X-Webhook-Secret, hodnota v .env jako
    ESIGNATURE_WEBHOOK_SECRET). Po potvrzení automaticky přechází
    Deal ze stavu Objednávka do Zálohová faktura a vytváří Document
    (Zálohová faktura).
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return perform_esignature_confirmation(db, deal)
