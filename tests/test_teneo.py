import pytest

from shared.teneo import OPTICAL_ZONES_MM, teneo_max_ablation


def test_only_6_and_6_5_mm_are_offered():
    assert OPTICAL_ZONES_MM == (6.0, 6.5)


@pytest.mark.parametrize(
    ("sphere", "zone", "ablation", "time_s", "zone_mm"),
    [
        (-3, 6.0, 44, 4, "7.2 x 7.2"),
        (-3, 6.5, 52, 5, "7.8 x 7.8"),
        (-10, 6.0, 132, 11, "7.7 x 7.7"),
        (-10, 6.5, 157, 15, "8.1 x 8.1"),
        (1, 6.0, 24, 3, "8.2 x 8.2"),
        (10, 6.0, 194, 25, "8.2 x 8.2"),
        (8, 6.5, 184, 27, "8.7 x 8.7"),
    ],
)
def test_exact_rows_match_the_spreadsheet(sphere, zone, ablation, time_s, zone_mm):
    result = teneo_max_ablation(sphere, zone)

    assert result.found is True
    assert result.interpolated is False
    assert (result.ablation_um, result.time_s, result.zone_mm) == (ablation, time_s, zone_mm)


def test_half_diopter_is_interpolated_and_rounded_up():
    result = teneo_max_ablation(-3.5, 6.0)  # entre 44 y 57 -> 50,5

    assert result.found is True
    assert result.interpolated is True
    assert result.ablation_um == 51


def test_hyperopia_interpolates_on_its_own_side():
    result = teneo_max_ablation(2.5, 6.0)  # entre 43 y 61 -> 52

    assert result.ablation_um == 52


@pytest.mark.parametrize(
    ("sphere", "zone"),
    [(0, 6.0), (-0.5, 6.0), (0.75, 6.5), (11, 6.0), (-10.5, 6.5), (9, 6.5), (9.5, 6.5), (-3, 5.0)],
)
def test_out_of_table_values_are_not_found_and_explain_why(sphere, zone):
    result = teneo_max_ablation(sphere, zone)

    assert result.found is False
    assert result.ablation_um == 0
    assert result.message


def test_cylinder_is_folded_into_the_spherical_equivalent():
    result = teneo_max_ablation(-3, 6.0, cylinder_d=-2)  # -4 D equivalentes

    assert result.found is True
    assert result.equivalent_d == -4
    assert result.ablation_um == 57


def test_equivalent_of_zero_is_not_found():
    result = teneo_max_ablation(-1, 6.0, cylinder_d=2)

    assert result.found is False
    assert "equivalente" in result.message
