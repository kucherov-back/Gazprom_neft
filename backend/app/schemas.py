from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    task_id: str = Field(description="ID созданной или дедуплицированной задачи")
    deduplicated: bool = Field(
        description="True, если вернули существующую задачу без новой обработки"
    )


class StatusCounts(BaseModel):
    pending: int = 0
    processing: int = 0
    done: int = 0
    error: int = 0


class StatsResponse(BaseModel):
    total: int
    by_status: StatusCounts
    avg_processing_seconds: float | None = None
    median_processing_seconds: float | None = None
    deduplicated_count: int


class ErrorResponse(BaseModel):
    detail: str
