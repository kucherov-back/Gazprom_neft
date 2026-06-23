"""
Генератор синтетических structlog-логов для задания.

Формат событий пайплайна: построчный JSON, московское время (UTC+3), парные события
start/end этапов, вызовы LLM/OCR с ретраями, ошибки. Намеренно подмешивает БИТЫЕ
строки (≈3%) — ETL должен быть к ним устойчив.

Запуск:  python generate_logs.py --tasks 200 --out sample_logs/app.log
"""
import argparse
import json
import random
from datetime import datetime, timedelta, timezone

MSK = timezone(timedelta(hours=3))
STAGES = ["preprocess", "completeness", "matching"]
MODELS = ["gemini-flash", "gpt-4o-mini", "qwen-72b"]
ERRORS = ["LLMTimeout", "OCRFailed", "ParseError", "ValidationError"]


def _ts(dt: datetime) -> str:
    return dt.astimezone(MSK).isoformat()


def gen(n_tasks: int):
    lines: list[str] = []
    clock = datetime(2026, 6, 1, 9, 0, tzinfo=MSK)

    for _ in range(n_tasks):
        clock += timedelta(seconds=random.randint(5, 120))
        task_id = f"t-{random.randint(10000, 99999)}"
        cur = clock
        failed = random.random() < 0.12

        lines.append(json.dumps({"ts": _ts(cur), "level": "info",
                                  "event": "task_started", "task_id": task_id}))

        for stage in STAGES:
            cur += timedelta(milliseconds=random.randint(50, 400))
            lines.append(json.dumps({"ts": _ts(cur), "level": "info",
                                     "event": "stage_start", "stage": stage, "task_id": task_id}))

            # вызовы LLM/OCR внутри этапа, с возможными ретраями
            for _ in range(random.randint(1, 4)):
                retries = random.choices([0, 1, 2], weights=[80, 15, 5])[0]
                cur += timedelta(milliseconds=random.randint(200, 3000))
                lines.append(json.dumps({
                    "ts": _ts(cur), "level": "info", "event": "llm_call",
                    "stage": stage, "task_id": task_id,
                    "model": random.choice(MODELS), "retries": retries,
                    "tokens": random.randint(200, 4000),
                }))

            dur = random.randint(300, 9000)
            cur += timedelta(milliseconds=dur)

            if failed and stage == random.choice(STAGES):
                lines.append(json.dumps({
                    "ts": _ts(cur), "level": "error", "event": "stage_error",
                    "stage": stage, "task_id": task_id, "error": random.choice(ERRORS),
                }))
                lines.append(json.dumps({"ts": _ts(cur), "level": "error",
                                         "event": "task_failed", "task_id": task_id}))
                break

            lines.append(json.dumps({
                "ts": _ts(cur), "level": "info", "event": "stage_end",
                "stage": stage, "task_id": task_id, "duration_ms": dur,
            }))
        else:
            lines.append(json.dumps({"ts": _ts(cur), "level": "info",
                                     "event": "task_done", "task_id": task_id}))

        # ≈3% битых строк: обрезанный JSON / мусор
        if random.random() < 0.03:
            lines.append('{"ts": "2026-06-01T10:00:00+03:00", "event": "stage_en')

    random.shuffle  # порядок в файле в целом хронологический; не перемешиваем
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=int, default=200)
    ap.add_argument("--out", default="sample_logs/app.log")
    args = ap.parse_args()

    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(gen(args.tasks)) + "\n")
    print(f"written -> {args.out}")


if __name__ == "__main__":
    main()
