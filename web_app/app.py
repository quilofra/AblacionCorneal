from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from shared.calculator import (
    PROCEDURE_CHOICES,
    EyeInput,
    compute_result,
    eye_result_to_dict,
)
from web_app.config import load_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "web_app" / "static"
ASSETS_DIR = PROJECT_ROOT / "assets"

settings = load_settings()

app = FastAPI(
    title="AblacionCorneal Web",
    summary="Calculadora web de seguridad para ablación corneal",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


class ComputeRequest(BaseModel):
    paqui_preop_um: int = Field(..., ge=0, le=2000)
    ablation_um: int = Field(default=0, ge=0, le=2000)
    suspicious: bool = False
    procedure: Literal["surface", "lasik", "smile"] = "surface"
    flap_cap_um: int = Field(default=0, ge=0, le=2000)
    legacy_mode: bool = False


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
def config() -> dict[str, object]:
    return {
        "app_name": settings.app_name,
        "github_repo_url": settings.github_repo_url,
        "desktop_download_url": settings.desktop_download_url,
        "procedure_choices": [
            {"value": value, "label": label} for value, label in PROCEDURE_CHOICES
        ],
    }


@app.post("/api/compute")
def compute(payload: ComputeRequest) -> dict[str, object]:
    result = compute_result(
        EyeInput(
            paqui_preop_um=payload.paqui_preop_um,
            ablation_um=payload.ablation_um,
            suspicious=payload.suspicious,
            procedure=payload.procedure,
            flap_cap_um=payload.flap_cap_um,
            legacy_mode=payload.legacy_mode,
        )
    )
    return eye_result_to_dict(result)
