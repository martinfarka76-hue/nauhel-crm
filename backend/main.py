import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app import models  # noqa: F401 - zajišťuje registraci modelů
from app.routers import (
    company, contact, deal, auth, calculation, document, webhooks, ares,
    stage_config, wood_species, pricing_parameter,
)
from app.core.scheduler import start_scheduler
from app.core.seed_data import seed_stage_config, seed_pricing_parameters, seed_wood_species
from app.database import SessionLocal

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        seed_stage_config(db)
        seed_pricing_parameters(db)
        seed_wood_species(db)
    finally:
        db.close()
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(title="NAUHEL CRM API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:18081", "http://localhost:18082"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Data nejde uložit - zkontroluj prosím, že odkazované záznamy "
            "(např. firma, kontakt) existují, a že jsou čísla ve správném formátu. "
            "Pokud mažeš záznam, na který se ještě něco odkazuje (např. firmu s "
            "existujícími obchodními případy), smaž nejdřív tyto navázané záznamy."
        },
    )


app.include_router(auth.router)
app.include_router(company.router)
app.include_router(contact.router)
app.include_router(deal.router)
app.include_router(calculation.router)
app.include_router(document.router)
app.include_router(webhooks.router)
app.include_router(ares.router)
app.include_router(stage_config.router)
app.include_router(wood_species.router)
app.include_router(pricing_parameter.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "nauhel-crm-backend"}


@app.get("/health")
def health():
    return {"status": "healthy"}
