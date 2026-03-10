from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

MAX_ABLATION_PCT = 20.0
LER_MIN_UM = 300
LER_PCT_NORMAL = 60.0
LER_PCT_SUSPICIOUS = 70.0
POSTOP_MIN_UM = 400
WARN_PAQUI_LOW = 470
WARN_PAQUI_HIGH = 500
MARGIN_UM = 20
MARGIN_PCT = 2.0

RuleStatus = Literal["pass", "warn", "fail"]
OverallStatus = Literal["ok", "warning", "fail", "invalid"]
ProcedureType = Literal["surface", "lasik", "smile"]

PROCEDURE_LABELS: dict[ProcedureType, str] = {
    "surface": "Superficie (PRK/PTK)",
    "lasik": "LASIK",
    "smile": "SMILE",
}
PROCEDURE_TISSUE_LABELS: dict[ProcedureType, str | None] = {
    "surface": None,
    "lasik": "Flap",
    "smile": "Cap",
}
PROCEDURE_CHOICES: tuple[tuple[ProcedureType, str], ...] = tuple(PROCEDURE_LABELS.items())


@dataclass
class EyeInput:
    paqui_preop_um: int
    ablation_um: int
    suspicious: bool = False
    procedure: ProcedureType = "surface"
    flap_cap_um: int = 0
    legacy_mode: bool = False


@dataclass
class EyeResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
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
    procedure: ProcedureType = "surface"
    procedure_label: str = "Superficie (PRK/PTK)"
    tissue_label: str = "Flap/Cap"
    flap_cap_um: int = 0
    legacy_mode: bool = False


def _status_from_margin(ok: bool, margin_um: float | None, margin_pct: float | None) -> RuleStatus:
    if not ok:
        return "fail"
    if margin_um is not None and margin_um < MARGIN_UM:
        return "warn"
    if margin_pct is not None and margin_pct < MARGIN_PCT:
        return "warn"
    return "pass"


def procedure_supports_flap_cap(procedure: ProcedureType) -> bool:
    return PROCEDURE_TISSUE_LABELS[procedure] is not None


def procedure_label(procedure: ProcedureType) -> str:
    return PROCEDURE_LABELS[procedure]


def procedure_tissue_label(procedure: ProcedureType) -> str:
    return PROCEDURE_TISSUE_LABELS[procedure] or "Flap/Cap"


def _effective_subtract_um(eye_input: EyeInput) -> int:
    if eye_input.legacy_mode:
        return 0
    if not procedure_supports_flap_cap(eye_input.procedure):
        return 0
    return eye_input.flap_cap_um


def validate_eye_input(eye_input: EyeInput) -> list[str]:
    errors: list[str] = []
    if eye_input.paqui_preop_um <= 0:
        errors.append("Introduce paquimetría preop.")
    if eye_input.ablation_um < 0:
        errors.append("Ablación no puede ser negativa.")
    if eye_input.flap_cap_um < 0:
        errors.append("Flap/Cap no puede ser negativo.")
    if eye_input.paqui_preop_um > 0 and eye_input.ablation_um > eye_input.paqui_preop_um:
        errors.append("Entradas inconsistentes: ablación supera paquimetría preop.")
    if (
        not eye_input.legacy_mode
        and procedure_supports_flap_cap(eye_input.procedure)
        and eye_input.flap_cap_um <= 0
    ):
        errors.append(
            f"Introduce espesor de {procedure_tissue_label(eye_input.procedure).lower()}."
        )

    subtract_um = _effective_subtract_um(eye_input)
    if eye_input.paqui_preop_um > 0 and subtract_um >= eye_input.paqui_preop_um:
        errors.append("Entradas inconsistentes: flap/cap supera paquimetría preop.")
    if (
        eye_input.paqui_preop_um > 0
        and subtract_um > 0
        and eye_input.ablation_um + subtract_um > eye_input.paqui_preop_um
    ):
        errors.append("Entradas inconsistentes: flap/cap + ablación supera paquimetría preop.")
    return errors


def compute_result(eye_input: EyeInput) -> EyeResult:
    errors = validate_eye_input(eye_input)
    if errors:
        return EyeResult(valid=False, errors=errors, overall_status="invalid")

    subtract_um = _effective_subtract_um(eye_input)
    paqui_preop_um = eye_input.paqui_preop_um
    ablation_um = eye_input.ablation_um

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
        tissue_label=procedure_tissue_label(eye_input.procedure),
        flap_cap_um=eye_input.flap_cap_um,
        legacy_mode=eye_input.legacy_mode,
    )
