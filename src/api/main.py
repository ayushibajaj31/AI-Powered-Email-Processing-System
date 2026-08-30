"""FastAPI entry point for the AI email-processing backend."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.email_routes import router as email_router
from src.api.health import database_health, rabbitmq_health
from src.auth.routes import router as auth_router
from src.config import settings


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = FastAPI(
    title="AI Email Processing System API",
    version="1.0.0",
    description="REST API for classifying customer emails, retrieving grounded context, and generating support responses.",
)
app.add_middleware(
    CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=True,
    allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization"],
)
app.include_router(auth_router)
app.include_router(email_router)


@app.get("/health", tags=["Health"], summary="Check whether the API server is running.")
def health_check():
    """Check API dependencies without loading the retriever or calling an LLM."""
    database = database_health()
    rabbitmq = rabbitmq_health()
    overall = "healthy" if database["status"] == rabbitmq["status"] == "healthy" else "degraded"
    return {"status": overall, "api": "healthy", "database": database["status"], "rabbitmq": rabbitmq["status"], "worker": rabbitmq["worker"]}
