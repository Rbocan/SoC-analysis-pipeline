from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


# ── Products ──────────────────────────────────────────────────────────────────

class MetricSpec(BaseModel):
    name: str
    unit: str
    min_val: float
    max_val: float
    nominal: float
    distribution: str = "normal"


class ProductOut(BaseModel):
    id: str
    name: str
    description: str
    metrics: list[MetricSpec]
    tests: list[str]
    data_source: str


# ── Data query ────────────────────────────────────────────────────────────────

class DataQuery(BaseModel):
    product_id: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    test_ids: Optional[list[str]] = None
    batch_ids: Optional[list[str]] = None
    status: Optional[str] = None
    limit: int = 1000
    offset: int = 0

    @field_validator("limit")
    @classmethod
    def cap_limit(cls, v: int) -> int:
        return min(v, 10_000)


class PivotRequest(BaseModel):
    product_id: str
    index: str = "batch_id"
    columns: str = "test_id"
    values: str = "voltage"
    agg_func: str = "mean"
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class ExportRequest(BaseModel):
    product_id: str
    format: str = "csv"
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ── Synthetic data ────────────────────────────────────────────────────────────

class SyntheticDataRequest(BaseModel):
    product_id: str
    num_records: int = 1000
    num_batches: int = 10
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    anomaly_rate: float = 0.02

    @field_validator("num_records")
    @classmethod
    def cap_records(cls, v: int) -> int:
        return min(v, 1_000_000)


# ── Reports ───────────────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    product_id: str
    report_type: str = "daily_validation"
    template: str = "daily_validation.html"
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    recipients: list[str] = []
    send_email: bool = False


class ReportOut(BaseModel):
    report_id: str
    product_id: str
    report_type: str
    template: str
    status: str
    file_path: Optional[str]
    generated_at: datetime

    model_config = {"from_attributes": True}


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    action: str
    resource: str
    details: Optional[dict[str, Any]]
    ip_address: Optional[str]
    timestamp: datetime

    model_config = {"from_attributes": True}


# ── Generic responses ─────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]
