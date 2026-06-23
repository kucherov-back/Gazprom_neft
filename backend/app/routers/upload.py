"""HTTP-слой: валидация запроса, вызов сервиса, маппинг в ответ."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.engine import get_session
from app.db.repositories import TaskRepository
from app.schemas import StatsResponse, UploadResponse
from app.services.task_service import TaskService, process_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["tasks"])


def get_task_service(session: AsyncSession = Depends(get_session)) -> TaskService:
    return TaskService(TaskRepository(session))


@router.post("/classify-zip/", response_model=UploadResponse)
async def classify_zip(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    force: bool = False,
    service: TaskService = Depends(get_task_service),
) -> UploadResponse:
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_size_mb} MB limit",
        )

    response, should_process = await service.classify_zip(
        content=content,
        filename=file.filename or "archive.zip",
        force=force,
    )
    if should_process:
        background_tasks.add_task(process_task, response.task_id)
    return response


@router.get("/stats", response_model=StatsResponse)
async def get_stats(service: TaskService = Depends(get_task_service)) -> StatsResponse:
    return await service.get_stats()
