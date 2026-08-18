from fastapi import FastAPI

from app import models  # noqa: F401 - zajišťuje registraci modelů

app = FastAPI(title="NAUHEL CRM API")


@app.get("/")
def root():
    return {"status": "ok", "service": "nauhel-crm-backend"}


@app.get("/health")
def health():
    return {"status": "healthy"}
