from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from shared.calculator import (
    DEFAULT_PROCEDURE,
    FLAP_THICKNESS_UM,
    PROCEDURE_CHOICES,
    EyeInput,
    compute_result,
    eye_result_to_dict,
)
from shared.teneo import DEFAULT_OPTICAL_ZONE_MM, OPTICAL_ZONES_MM
from web_app.config import load_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "web_app" / "static"
ASSETS_DIR = PROJECT_ROOT / "assets"

settings = load_settings()

app = FastAPI(
    title="AblacionCorneal Web",
    summary="Calculadora web de seguridad para ablación corneal",
)


def _asset_version() -> str:
    """Huella del CSS/JS: cambia en cada despliegue y rompe cachés viejas (navegador y Cloudflare)."""
    digest = hashlib.sha1()
    for name in ("app.js", "app.css"):
        digest.update((STATIC_DIR / name).read_bytes())
    return digest.hexdigest()[:10]


ASSET_VERSION = _asset_version()


@app.middleware("http")
async def revalidate_static(request: Request, call_next) -> Response:
    # Sin esto, Cloudflare y los navegadores guardaban app.js/app.css 4 h y se mezclaban versiones.
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith(("/static/", "/assets/")):
        response.headers["Cache-Control"] = "no-cache"
    return response


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


class ComputeRequest(BaseModel):
    paqui_preop_um: int = Field(..., ge=0, le=2000)
    # Ablación directa, o graduación (esfera/cilindro + zona óptica) para sacarla de la tabla.
    ablation_um: int | None = Field(default=None, ge=0, le=2000)
    sphere_d: float | None = Field(default=None, ge=-30, le=30)
    cylinder_d: float = Field(default=0.0, ge=-15, le=15)
    optical_zone_mm: float = DEFAULT_OPTICAL_ZONE_MM
    suspicious: bool = False
    procedure: Literal["lasik", "prk"] = "lasik"


@app.get("/", include_in_schema=False)
def index() -> HTMLResponse:
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html.replace("__ASSET_VERSION__", ASSET_VERSION))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
def config() -> dict[str, object]:
    return {
        "app_name": settings.app_name,
        "github_repo_url": settings.github_repo_url,
        "desktop_download_url": settings.desktop_download_url,
        "default_procedure": DEFAULT_PROCEDURE,
        "optical_zone_choices": list(OPTICAL_ZONES_MM),
        "default_optical_zone_mm": DEFAULT_OPTICAL_ZONE_MM,
        "flap_um": FLAP_THICKNESS_UM,
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
            sphere_d=payload.sphere_d,
            cylinder_d=payload.cylinder_d,
            optical_zone_mm=payload.optical_zone_mm,
        )
    )
    return eye_result_to_dict(result)
