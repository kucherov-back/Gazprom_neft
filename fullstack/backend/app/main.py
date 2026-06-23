"""
Бэкенд для «Regex Lab».

Эндпоинт /api/regex/suggest намеренно не дореализован — это часть задачи.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.utils.llm_client import LLMClient

app = FastAPI(title="Regex Lab — backend")

# CORS открыт, чтобы Vite dev-сервер ходил на бэкенд без боли.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


class SuggestRequest(BaseModel):
    text: str
    positives: list[str]
    negatives: list[str] = []


class SuggestResponse(BaseModel):
    pattern: str
    flags: str = "IGNORECASE"
    explanation: str = ""


@app.post("/api/regex/suggest", response_model=SuggestResponse)
async def suggest_regex(req: SuggestRequest) -> SuggestResponse:
    llm = LLMClient()
    # TODO(кандидат):
    #   1. Собрать осмысленный промпт из text/positives/negatives.
    #   2. Вызвать llm.complete(...) и БЕЗОПАСНО распарсить JSON (ответ бывает в ```json```).
    #   3. Скомпилировать regex; проверить, что он матчит ВСЕ позитивы и НЕ матчит негативы.
    #      Если не сошлось — вернуть осмысленную ошибку (HTTP 422) или попробовать ретрай.
    raw = await llm.complete(system="заполни меня", user="заполни меня")  # noqa: F841
    return SuggestResponse(pattern="", flags="IGNORECASE", explanation="не реализовано")


@app.get("/health")
async def health():
    return {"status": "ok"}
