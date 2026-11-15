import pytest

from shared.calculator import EyeInput, compute_result


def test_basic_surface_pass():
    result = compute_result(
        EyeInput(
            paqui_preop_um=500,
            ablation_um=80,
            suspicious=False,
        )
    )

    assert result.valid is True
    assert result.subtract_um == 0
    assert result.rule_ablation_status == "pass"
    assert result.rule_ler_um_status == "pass"
    assert result.rule_ler_pct_status == "pass"
    assert result.rule_postop_status == "pass"
    assert result.overall_status == "ok"
    assert pytest.approx(result.ablation_pct, rel=1e-3) == 16.0


def test_suspicious_threshold_fail():
    result = compute_result(
        EyeInput(
            paqui_preop_um=500,
            ablation_um=180,
            suspicious=True,
        )
    )

    assert result.rule_ler_pct_status == "fail"
    assert result.overall_status == "fail"


def test_edge_ler_um_warn():
    result = compute_result(
        EyeInput(
            paqui_preop_um=500,
            ablation_um=200,
            suspicious=False,
        )
    )

    assert result.ler_um == 300
    assert result.rule_ler_um_status == "warn"


def test_edge_postop_warn():
    result = compute_result(
        EyeInput(
            paqui_preop_um=500,
            ablation_um=100,
            suspicious=False,
        )
    )

    assert result.postop_paqui_um == 400
    assert result.rule_postop_status == "warn"


def test_edge_ablation_pct_warn():
    result = compute_result(
        EyeInput(
            paqui_preop_um=500,
            ablation_um=100,
            suspicious=False,
        )
    )

    assert pytest.approx(result.ablation_pct, rel=1e-3) == 20.0
    assert result.rule_ablation_status == "warn"


def test_lasik_uses_flap_cap():
    result = compute_result(
        EyeInput(
            paqui_preop_um=500,
            ablation_um=80,
            suspicious=False,
            procedure="lasik",
            flap_cap_um=110,
        )
    )

    assert result.valid is True
    assert result.subtract_um == 110
    assert result.ler_um == 310
    assert result.rule_ler_um_status == "warn"
    assert result.limit_factor == "LER µm"
    assert result.ablation_max_safe_um == 90


def test_surface_ignores_flap_cap():
    result = compute_result(
        EyeInput(
            paqui_preop_um=500,
            ablation_um=80,
            suspicious=False,
            procedure="surface",
            flap_cap_um=120,
        )
    )

    assert result.valid is True
    assert result.subtract_um == 0
    assert result.ler_um == 420


def test_missing_flap_cap_is_invalid_for_lasik():
    result = compute_result(
        EyeInput(
            paqui_preop_um=500,
            ablation_um=80,
            suspicious=False,
            procedure="lasik",
            flap_cap_um=0,
        )
    )

    assert result.valid is False
    assert result.overall_status == "invalid"
    assert result.errors[0] == "Introduce espesor de flap."


def test_flap_cap_plus_ablation_cannot_exceed_preop():
    result = compute_result(
        EyeInput(
            paqui_preop_um=450,
            ablation_um=200,
            suspicious=False,
            procedure="lasik",
            flap_cap_um=300,
        )
    )

    assert result.valid is False
    assert result.overall_status == "invalid"
    assert "flap/cap + ablación" in result.errors[0]


def test_inconsistent_inputs_invalid():
    result = compute_result(
        EyeInput(
            paqui_preop_um=400,
            ablation_um=450,
            suspicious=False,
        )
    )

    assert result.valid is False
    assert result.overall_status == "invalid"


def test_default_flap_is_120_and_lasik_is_default_procedure():
    from shared import DEFAULT_FLAP_CAP_UM, DEFAULT_PROCEDURE

    assert DEFAULT_FLAP_CAP_UM == 120
    assert DEFAULT_PROCEDURE == "lasik"


def test_lasik_default_flap_is_subtracted_from_residual_bed():
    from shared import DEFAULT_FLAP_CAP_UM

    result = compute_result(
        EyeInput(paqui_preop_um=540, ablation_um=80, procedure="lasik", flap_cap_um=DEFAULT_FLAP_CAP_UM)
    )

    assert result.valid
    assert result.subtract_um == 120
    assert result.ler_um == 540 - 120 - 80
