"""Public API schemas for email processing."""

from pydantic import BaseModel, ConfigDict, Field


class EmailProcessRequest(BaseModel):
    """An email and optional explicit IDs used for verified record lookups."""
    model_config = ConfigDict(extra="forbid")
    subject: str = Field(..., min_length=1, max_length=500, description="Customer email subject.")
    email_body: str = Field(..., min_length=1, max_length=10_000, description="Customer email body; must not be empty.")
    order_id: str | None = Field(None, max_length=50, description="Optional existing order ID.")
    product_id: str | None = Field(None, max_length=50, description="Optional existing product ID.")


class EmailQueuedResponse(BaseModel):
    job_id: str
    status: str
    message: str


class EmailJobStatusResponse(BaseModel):
    job_id: str
    status: str
    predicted_category: str | None = None
    response: str | None = None
    sources: list[dict] | None = None
    processing_time: float | None = None


class RetrievedSource(BaseModel):
    chunk_id: str
    topic: str
    category: str
    score: float


class EmailProcessResponse(BaseModel):
    predicted_category: str
    response: str
    sources: list[RetrievedSource]
    processing_time: float = Field(..., description="Total local API processing time in seconds.")
