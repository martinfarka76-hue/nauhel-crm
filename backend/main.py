from fastapi import FastAPI

from app import models  # noqa: F401 - zajišťuje registraci modelů
from app.routers import company, contact, deal

app = FastAPI(title="NAUHEL CRM API")

app.include_router(company.router)
app.include_router(contact.router)
app.include_router(deal.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "nauhel-crm-backend"}


@app.get("/health")
def health():
    return {"status": "healthy"}
