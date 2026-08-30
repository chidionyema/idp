"""${{ values.description }}

The service the golden path made. /healthz is what the cluster and the login drill read.
"""
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from . import tracing

tracing.configure()
app = FastAPI(title="${{ values.name }}")
FastAPIInstrumentor.instrument_app(app)


@app.get("/healthz")
def healthz() -> dict:
    return {"service": "${{ values.name }}", "ok": True}


@app.get("/")
def home() -> dict:
    return {"service": "${{ values.name }}", "description": "${{ values.description }}"}
