from pydantic import BaseModel


class UploadResponse(BaseModel):
    task_id: str
    deduplicated: bool


class StatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    avg_processing_seconds: float | None
    median_processing_seconds: float | None
    deduplicated_count: int