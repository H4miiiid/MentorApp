from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field


class GradingModelRead(BaseModel):
    id: str
    display_name: str
    notes: str
    openai_model_name: str
    n_ctx: int = 8192
    is_active: bool
    created_at: datetime
    updated_at: datetime


class GradingModelCreate(BaseModel):
    display_name: str = Field(max_length=200)
    notes: str = Field(
        default="",
        max_length=512,
        validation_alias=AliasChoices("notes", "gguf_filename"),
    )
    openai_model_name: str = Field(max_length=200)
    n_ctx: int = Field(default=8192, ge=256, le=131072)


class GradingModelUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(
        default=None,
        max_length=512,
        validation_alias=AliasChoices("notes", "gguf_filename"),
    )
    openai_model_name: str | None = Field(default=None, max_length=200)
    n_ctx: int | None = Field(default=None, ge=256, le=131072)


class GradingStatusResponse(BaseModel):
    """HF endpoint HTTP health + active catalog row (for admin diagnostics)."""

    endpoint_health_ok: bool
    endpoint_health_url: str
    hf_inference_base_url: str
    active_model: GradingModelRead | None
    endpoint_health_error: str | None = None
    note: str
