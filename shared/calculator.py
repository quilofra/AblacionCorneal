from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Literal

from .teneo import DEFAULT_OPTICAL_ZONE_MM, LaserAblation, teneo_max_ablation

MAX_ABLATION_PCT = 20.0
LER_MIN_UM = 300
LER_PCT_NORMAL = 60.0
LER_PCT_SUSPICIOUS = 70.0
POSTOP_MIN_UM = 400
WARN_PAQUI_LOW = 470
WARN_PAQUI_HIGH = 500
MARGIN_UM = 20
MARGIN_PCT = 2.0
FLAP_THICKNESS_UM = 120
DEFAULT_PROCEDURE = "lasik"

RuleStatus = Literal["pass", "warn", "fail"]
OverallStatus = Literal["ok", "warning", "fail", "invalid"]
ProcedureType = Literal["lasik", "prk"]

PROCEDURE_LABELS: dict[ProcedureType, str] = {
    "lasik": "LASIK",
    "prk": "PRK",
}
PROCEDURE_CHOICES: tuple[tuple[ProcedureType, str], ...] = tuple(PROCEDURE_LABELS.items())


@dataclass
class EyeInput:
    """Caso a evaluar.

    La ablación se da directamente (`ablation_um`) o se calcula con la tabla del láser a partir
    de la graduación (`sphere_d` + `cylinder_d`) y la zona óptica; si hay esfera, manda la tabla.
    """

    paqui_preop_um: int
    ablation_um: int | None = None
    suspicious: bool = False
    procedure: ProcedureType = "lasik"
    sphere_d: float | None = None
    cylinder_d: float = 0.0
    optical_zone_mm: float = DEFAULT_OPTICAL_ZONE_MM


@dataclass
class EyeResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    ablation_um: int = 0
    laser: LaserAblation | None = None
    ablation_pct: float = 0.0
    subtract_um: int = 0
    ler_um: int = 0
    ler_pct: float = 0.0
    postop_paqui_um: int = 0
    ler_pct_threshold: float = LER_PCT_NORMAL
    ablation_pct_threshold: float = MAX_ABLATION_PCT
    ler_um_threshold: int = LER_MIN_UM
    postop_um_threshold: int = POSTOP_MIN_UM
    rule_ablation_status: RuleStatus = "fail"
    rule_ler_um_status: RuleStatus = "fail"
    rule_ler_pct_status: RuleStatus = "fail"
    rule_postop_status: RuleStatus = "fail"
    overall_status: OverallStatus = "invalid"
    limit_factor: str = ""
    ablation_max_safe_um: int = 0
    margin_um: int = 0
    procedure: ProcedureType = "lasik"
    procedure_label: str = "LASIK"


def eye_result_to_dict(result: EyeResult) -> dict[str, object]:
    return asdict(result)


def _status_from_margin(ok: bool, margin_um: float | None, margin_pct: float | None) -> RuleStatus:
    if not ok:
        return "fail"
    if margin_um is not None and margin_um < MARGIN_UM:
        return "warn"
    if margin_pct is not None and margin_pct < MARGIN_PCT:
        return "warn"
    return "pass"


def procedure_has_flap(procedure: ProcedureType) -> bool:
    return procedure == "lasik"


def procedure_label(procedure: ProcedureType) -> str:
    return PROCEDURE_LABELS[procedure]


def flap_um(procedure: ProcedureType) -> int:
    """Micras que se restan del lecho por el flap: 120 en LASIK, 0 en PRK."""
    return FLAP_THICKNESS_UM if procedure_has_flap(procedure) else 0


def _resolve_ablation(eye_input: EyeInput) -> tuple[int | None, LaserAblation | None, list[str]]:
    """Ablación a usar: la de la tabla si hay graduación, o la dada directamente."""
    if eye_input.sphere_d is not None:
        laser = teneo_max_ablation(
            eye_input.sphere_d, eye_input.optical_zone_mm, eye_input.cylinder_d
        )
        if not laser.found:
            return None, laser, [laser.message]
        return laser.ablation_um, laser, []
    if eye_input.ablation_um is None:
        return None, None, ["Introduce la graduación o la ablación."]
    return eye_input.ablation_um, None, []


def validate_eye_input(eye_input: EyeInput, ablation_um: int | None = None) -> list[str]:
    errors: list[str] = []
    if eye_input.paqui_preop_um <= 0:
        errors.append("Introduce paquimetría preop.")
    if ablation_um is None:
        return errors
    if ablation_um < 0:
        errors.append("Ablación no puede ser negativa.")
    if eye_input.paqui_preop_um > 0 and ablation_um > eye_input.paqui_preop_um:
        errors.append("Entradas inconsistentes: ablación supera paquimetría preop.")

    flap = flap_um(eye_input.procedure)
    if eye_input.paqui_preop_um > 0 and flap >= eye_input.paqui_preop_um:
        errors.append("Entradas inconsistentes: flap supera paquimetría preop.")
    elif eye_input.paqui_preop_um > 0 and flap > 0 and ablation_um + flap > eye_input.paqui_preop_um:
        errors.append("Entradas inconsistentes: flap + ablación supera paquimetría preop.")
    return errors


def compute_result(eye_input: EyeInput) -> EyeResult:
    ablation_um, laser, resolve_errors = _resolve_ablation(eye_input)
    errors = resolve_errors + validate_eye_input(eye_input, ablation_um)
    if errors or ablation_um is None:
        return EyeResult(valid=False, errors=errors, overall_status="invalid", laser=laser)

    subtract_um = flap_um(eye_input.procedure)
    paqui_preop_um = eye_input.paqui_preop_um

    ablation_pct = (ablation_um / paqui_preop_um) * 100.0
    ler_um = paqui_preop_um - subtract_um - ablation_um
    ler_pct = (ler_um / paqui_preop_um) * 100.0
    postop_paqui_um = paqui_preop_um - ablation_um

    ler_pct_threshold = LER_PCT_SUSPICIOUS if eye_input.suspicious else LER_PCT_NORMAL

    ablation_ok = ablation_pct <= MAX_ABLATION_PCT
    ler_um_ok = ler_um >= LER_MIN_UM
    ler_pct_ok = ler_pct >= ler_pct_threshold
    postop_ok = postop_paqui_um >= POSTOP_MIN_UM

    ablation_pct_margin = MAX_ABLATION_PCT - ablation_pct
    ler_um_margin = ler_um - LER_MIN_UM
    ler_pct_margin = ler_pct - ler_pct_threshold
    postop_um_margin = postop_paqui_um - POSTOP_MIN_UM

    rule_ablation_status = _status_from_margin(ablation_ok, None, ablation_pct_margin)
    rule_ler_um_status = _status_from_margin(ler_um_ok, ler_um_margin, None)
    rule_ler_pct_status = _status_from_margin(ler_pct_ok, None, ler_pct_margin)
    rule_postop_status = _status_from_margin(postop_ok, postop_um_margin, None)

    overall_status: OverallStatus = "ok"
    if "fail" in {rule_ablation_status, rule_ler_um_status, rule_ler_pct_status, rule_postop_status}:
        overall_status = "fail"
    elif "warn" in {rule_ablation_status, rule_ler_um_status, rule_ler_pct_status, rule_postop_status}:
        overall_status = "warning"

    abl_max_1 = (MAX_ABLATION_PCT / 100.0) * paqui_preop_um
    abl_max_2 = paqui_preop_um - subtract_um - LER_MIN_UM
    abl_max_3 = paqui_preop_um - subtract_um - (ler_pct_threshold / 100.0) * paqui_preop_um
    abl_max_4 = paqui_preop_um - POSTOP_MIN_UM

    factors = [
        ("Ablación %", abl_max_1),
        ("LER µm", abl_max_2),
        ("LER %", abl_max_3),
        ("Paqui post-op", abl_max_4),
    ]
    limit_factor, limit_value = min(factors, key=lambda item: item[1])
    ablation_max_safe_um = max(0, math.floor(limit_value))
    margin_um = ablation_max_safe_um - ablation_um

    return EyeResult(
        valid=True,
        errors=[],
        ablation_um=ablation_um,
        laser=laser,
        ablation_pct=ablation_pct,
        subtract_um=subtract_um,
        ler_um=ler_um,
        ler_pct=ler_pct,
        postop_paqui_um=postop_paqui_um,
        ler_pct_threshold=ler_pct_threshold,
        ablation_pct_threshold=MAX_ABLATION_PCT,
        ler_um_threshold=LER_MIN_UM,
        postop_um_threshold=POSTOP_MIN_UM,
        rule_ablation_status=rule_ablation_status,
        rule_ler_um_status=rule_ler_um_status,
        rule_ler_pct_status=rule_ler_pct_status,
        rule_postop_status=rule_postop_status,
        overall_status=overall_status,
        limit_factor=limit_factor,
        ablation_max_safe_um=ablation_max_safe_um,
        margin_um=margin_um,
        procedure=eye_input.procedure,
        procedure_label=procedure_label(eye_input.procedure),
    )
