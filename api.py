"""
HTTP API：多 Agent 专利估值流水线

启动（本地）:
  uvicorn api:app --reload --port 8000

Docker:
  docker compose up -d
  curl http://localhost:8000/health
  curl -X POST http://localhost:8000/valuate/CN202320045678.9
"""

from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.agents.pipeline import run_pipeline, run_pipeline_from_file

app = FastAPI(
    title="化学领域专利创新估值 Agent",
    description="创新程度 → 应用场景 → 市场环境 → 价值整合 → 估值 → 报告",
    version="0.2.0",
)


class ValuateOptions(BaseModel):
    save: bool = True


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/valuate/{patent_id}")
def valuate(patent_id: str, options: ValuateOptions | None = None) -> dict:
    opts = options or ValuateOptions()
    try:
        report = run_pipeline(patent_id, save=opts.save)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return report.report_json


@app.get("/valuate/{patent_id}")
def valuate_get(patent_id: str) -> dict:
    return valuate(patent_id)


@app.post("/valuate/file")
async def valuate_file(
    file: UploadFile = File(..., description="专利 txt / json / pdf"),
    save: bool = False,
) -> dict:
    """上传本地专利文件，直接运行六 Agent 估值。"""
    suffix = (file.filename or "upload.txt").rsplit(".", 1)[-1].lower()
    if suffix not in ("txt", "md", "json", "pdf"):
        raise HTTPException(
            status_code=400,
            detail="仅支持 .txt .md .json .pdf",
        )
    import tempfile
    from pathlib import Path

    tmp_path: str | None = None
    try:
        body = await file.read()
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{suffix}"
        ) as tmp:
            tmp.write(body)
            tmp_path = tmp.name
        report = run_pipeline_from_file(tmp_path, save=save)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass
    return report.report_json
