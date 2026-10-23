"""
Audit Trail and Benchmark Schemas.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class AuditLogResponse(BaseModel):
    id: str
    actor_id: Optional[str]
    actor_email: Optional[str]
    action: str
    resource_type: str
    resource_id: str
    details_json: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True

class ModelBenchmarkResponse(BaseModel):
    id: str
    model_name: str
    quantization: Optional[str]
    task_type: str
    latency_ms: float
    tokens_per_second: Optional[float]
    memory_mb: Optional[float]
    success: bool
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
