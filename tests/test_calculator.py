import pytest

from shared import DEFAULT_PROCEDURE, FLAP_THICKNESS_UM, PROCEDURE_CHOICES
from shared.calculator import EyeInput, compute_result


def prk(paqui: int, ablation: int, suspicious: bool = False):
    return compute_result(
        EyeInput(paqui_preop_um=paqui, ablation_um=ablation, suspicious=suspicious, procedure="prk")
    )


def lasik(paqui: int, ablation: int, suspicious: bool = False):
    return compute_result(
        EyeInput(paqui_preop_um=paqui, ablation_um=ablation, suspicious=suspicious, procedure="lasik")
    )


def test_only_lasik_and_prk_are_offered():
    assert [value for value, _label in PROCEDURE_CHOICES] == ["lasik", "prk"]
    assert DEFAULT_PROCEDURE == "lasik"
    assert FLAP_THICKNESS_UM == 120


def test_basic_prk_pass():
    result = prk(500, 80)

    assert result.valid is True
    assert result.subtract_um == 0
    assert result.ler_um == 420
    assert result.rule_ablation_status == "pass"
    assert result.rule_ler_um_status == "pass"
    assert result.rule_ler_pct_status == "pass"
    assert result.rule_postop_status == "pass"
    assert result.overall_status == "ok"
    assert pytest.approx(result.ablation_pct, rel=1e-3) == 16.0


def test_lasik_always_subtracts_the_120_um_flap():
    result = lasik(540, 80)

    assert result.valid is True
    assert result.subtract_um == 120
    assert result.ler_um == 540 - 120 - 80
    # La paquimetría post-op es la córnea entera: el flap sigue ahí.
    assert result.postop_paqui_um == 540 - 80


def test_prk_never_subtracts_a_flap():
    assert prk(540, 80).ler_um == 460


def test_lasik_limit_uses_flap():
    result = lasik(500, 80)

    assert result.ler_um == 300
    assert result.rule_ler_um_status == "warn"
    assert result.limit_factor == "LER µm"
    assert result.ablation_max_safe_um == 80


def test_suspicious_threshold_fail():
    result = prk(500, 180, suspicious=True)

    assert result.rule_ler_pct_status == "fail"
    assert result.overall_status == "fail"


def test_edge_ler_um_warn():
    result = prk(500, 200)

    assert result.ler_um == 300
    assert result.rule_ler_um_status == "warn"


def test_edge_postop_warn():
    result = prk(500, 100)

    assert result.postop_paqui_um == 400
    assert result.rule_postop_status == "warn"


def test_edge_ablation_pct_warn():
    result = prk(500, 100)

    assert pytest.approx(result.ablation_pct, rel=1e-3) == 20.0
    assert result.rule_ablation_status == "warn"


def test_flap_plus_ablation_cannot_exceed_preop():
    result = lasik(450, 340)

    assert result.valid is False
    assert result.overall_status == "invalid"
    assert "flap + ablación" in result.errors[0]


def test_ablation_cannot_exceed_preop():
    result = prk(400, 450)

    assert result.valid is False
    assert result.overall_status == "invalid"


def test_missing_ablation_and_graduation_is_invalid():
    result = compute_result(EyeInput(paqui_preop_um=500, procedure="prk"))

    assert result.valid is False
    assert result.errors == ["Introduce la graduación o la ablación."]


def test_graduation_takes_the_ablation_from_the_table():
    result = compute_result(
        EyeInput(paqui_preop_um=540, sphere_d=-3, optical_zone_mm=6.0, procedure="lasik")
    )

    assert result.valid is True
    assert result.ablation_um == 44
    assert result.laser is not None and result.laser.found
    assert result.ler_um == 540 - 120 - 44


def test_graduation_in_prk_does_not_subtract_flap():
    result = compute_result(
        EyeInput(paqui_preop_um=540, sphere_d=-3, optical_zone_mm=6.5, procedure="prk")
    )

    assert result.ablation_um == 52
    assert result.subtract_um == 0
    assert result.ler_um == 540 - 52


def test_cylinder_uses_the_spherical_equivalent():
    result = compute_result(
        EyeInput(paqui_preop_um=540, sphere_d=-3, cylinder_d=-2, optical_zone_mm=6.0, procedure="prk")
    )

    # -3 + (-2/2) = -4 D equivalentes
    assert result.laser.equivalent_d == -4
    assert result.ablation_um == 57


def test_graduation_wins_over_a_typed_ablation():
    result = compute_result(
        EyeInput(paqui_preop_um=540, ablation_um=10, sphere_d=-3, optical_zone_mm=6.0, procedure="prk")
    )

    assert result.ablation_um == 44


def test_graduation_outside_the_table_is_invalid_with_reason():
    result = compute_result(
        EyeInput(paqui_preop_um=540, sphere_d=9, optical_zone_mm=6.5, procedure="lasik")
    )

    assert result.valid is False
    assert "Sin datos" in result.errors[0]


def test_prk_paqui_preop_minimum_450_460():
    from shared.calculator import EyeInput, compute_result

    def prk(paqui, ablation=40):
        return compute_result(EyeInput(paqui_preop_um=paqui, ablation_um=ablation, procedure="prk"))

    assert prk(440).rule_paqui_prk_status == "fail"
    assert prk(440).overall_status == "fail"
    assert prk(449).rule_paqui_prk_status == "fail"
    assert prk(450).rule_paqui_prk_status == "warn"
    assert prk(459).rule_paqui_prk_status == "warn"
    assert prk(460).rule_paqui_prk_status == "pass"
    # el final sigue siendo ≥ 400 µm
    assert prk(500, 100).postop_paqui_um == 400
    assert prk(500, 120).rule_postop_status == "fail"


def test_prk_paqui_rule_does_not_apply_to_lasik():
    from shared.calculator import EyeInput, compute_result

    result = compute_result(EyeInput(paqui_preop_um=440, ablation_um=10, procedure="lasik"))
    assert result.rule_paqui_prk_status is None
