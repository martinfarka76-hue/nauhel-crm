import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401 - zajišťuje registraci modelů
from app.routers import company, contact, deal, auth, calculation, document, webhooks
from app.core.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(title="NAUHEL CRM API", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(company.router)
app.include_router(contact.router)
app.include_router(deal.router)
app.include_router(calculation.router)
app.include_router(document.router)
app.include_router(webhooks.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "nauhel-crm-backend"}


@app.get("/health")
def health():
    return {"status": "healthy"}
