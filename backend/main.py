import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app import models  # noqa: F401 - zajišťuje registraci modelů
from app.routers import (
    company, contact, deal, auth, calculation, document, webhooks, ares,
    stage_config, wood_species, pricing_parameter, user, notification,
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


app = FastAPI(
    title="NAUHEL CRM API",
    lifespan=lifespan,
    # Swagger (/docs, /redoc, /openapi.json) lze vypnout přes .env
    # (API_DOCS_ENABLED=false) - důležité, pokud je API vystrčené na
    # veřejný internet (Cloudflare Tunnel apod.), ať nikdo zvenčí nevidí
    # mapu celého API bez přihlášení.
    docs_url="/docs" if os.environ.get("API_DOCS_ENABLED", "true").lower() != "false" else None,
    redoc_url="/redoc" if os.environ.get("API_DOCS_ENABLED", "true").lower() != "false" else None,
    openapi_url="/openapi.json" if os.environ.get("API_DOCS_ENABLED", "true").lower() != "false" else None,
)

# CORS origins konfigurovatelné přes .env (CORS_ALLOWED_ORIGINS, čárkou
# oddělený seznam) - ať se dá snadno přidat veřejnou doménu (Cloudflare
# Tunnel apod.) bez nutnosti měnit kód, jen upravit .env a restartovat.
_default_origins = "http://localhost:18081,http://localhost:18082"
_cors_origins = os.environ.get("CORS_ALLOWED_ORIGINS", _default_origins)
allowed_origins = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
app.include_router(user.router)
app.include_router(notification.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "nauhel-crm-backend"}


@app.get("/health")
def health():
    return {"status": "healthy"}
