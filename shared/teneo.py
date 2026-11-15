"""Tabla de ablación máxima del láser Teneo por esfera y zona óptica.

Datos de «ablación Teneo.xlsx». Cada fila es (esfera D, zona 6 mm, zona 6,5 mm) y cada zona es
(tiempo s, ablación máx. µm, zona de tratamiento mm) o None cuando la tabla no tiene dato.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

OPTICAL_ZONES_MM: tuple[float, ...] = (6.0, 6.5)
DEFAULT_OPTICAL_ZONE_MM = 6.0
MAX_SPHERE_D = 10

_ZoneData = tuple[int, int, str] | None

_TABLE: tuple[tuple[int, _ZoneData, _ZoneData], ...] = (
    (+10, (25, 194, '8.2 x 8.2'), None),
    (+9, (22, 173, '8.2 x 8.2'), None),
    (+8, (20, 154, '8.2 x 8.2'), (27, 184, '8.7 x 8.7')),
    (+7, (18, 135, '8.2 x 8.2'), (23, 161, '8.7 x 8.7')),
    (+6, (15, 116, '8.2 x 8.2'), (20, 139, '8.7 x 8.7')),
    (+5, (13, 98, '8.2 x 8.2'), (17, 116, '8.7 x 8.7')),
    (+4, (10, 79, '8.2 x 8.2'), (14, 93, '8.7 x 8.7')),
    (+3, (8, 61, '8.2 x 8.2'), (11, 73, '8.7 x 8.7')),
    (+2, (6, 43, '8.2 x 8.2'), (7, 50, '8.7 x 8.7')),
    (+1, (3, 24, '8.2 x 8.2'), (4, 28, '8.7 x 8.7')),
    (-1, (2, 18, '7.1 x 7.1'), (2, 21, '7.6 x 7.6')),
    (-2, (3, 31, '7.2 x 7.2'), (4, 37, '7.7 x 7.7')),
    (-3, (4, 44, '7.2 x 7.2'), (5, 52, '7.8 x 7.8')),
    (-4, (5, 57, '7.3 x 7.3'), (7, 68, '7.9 x 7.9')),
    (-5, (6, 70, '7.4 x 7.4'), (8, 83, '7.9 x 7.9')),
    (-6, (7, 81, '7.4 x 7.4'), (9, 97, '8.1 x 8.1')),
    (-7, (8, 95, '7.5 x 7.5'), (11, 111, '8.1 x 8.1')),
    (-8, (9, 105, '7.5 x 7.6'), (12, 127, '8.1 x 8.2')),
    (-9, (10, 120, '7.6 x 7.7'), (14, 142, '8.2 x 8.3')),
    (-10, (11, 132, '7.7 x 7.7'), (15, 157, '8.1 x 8.1')),
)

_BY_SPHERE: dict[int, dict[float, _ZoneData]] = {
    sphere: {6.0: zone_6, 6.5: zone_65} for sphere, zone_6, zone_65 in _TABLE
}


@dataclass
class LaserAblation:
    found: bool
    sphere_d: float = 0.0
    cylinder_d: float = 0.0
    equivalent_d: float = 0.0
    optical_zone_mm: float = DEFAULT_OPTICAL_ZONE_MM
    ablation_um: int = 0
    time_s: int | None = None
    zone_mm: str = ""
    interpolated: bool = False
    message: str = ""


def laser_ablation_to_dict(result: LaserAblation) -> dict[str, object]:
    return asdict(result)


def _fmt_d(value: float) -> str:
    return f"{value:+g}".replace(".", ",")


def _fail(
    sphere_d: float, cylinder_d: float, equivalent_d: float, optical_zone_mm: float, message: str
) -> LaserAblation:
    return LaserAblation(
        found=False,
        sphere_d=sphere_d,
        cylinder_d=cylinder_d,
        equivalent_d=equivalent_d,
        optical_zone_mm=optical_zone_mm,
        message=message,
    )


def teneo_max_ablation(
    sphere_d: float, optical_zone_mm: float, cylinder_d: float = 0.0
) -> LaserAblation:
    """Ablación máxima (µm) de la tabla para una graduación y una zona óptica.

    La tabla solo tiene esfera: con cilindro se busca la esfera equivalente (esfera + cilindro/2).

    Entre dos filas enteras de la misma dirección (miopía o hipermetropía) se interpola
    linealmente y se redondea hacia arriba, para no quedarse corto.
    """
    zone = round(float(optical_zone_mm), 1)
    equivalent_d = round(sphere_d + cylinder_d / 2, 4)
    args = (sphere_d, cylinder_d, equivalent_d, zone)
    if zone not in OPTICAL_ZONES_MM:
        return _fail(*args, "Zona óptica no disponible en la tabla.")
    if equivalent_d == 0:
        return _fail(*args, "La esfera equivalente es 0: introduce una graduación distinta de 0.")

    magnitude = abs(equivalent_d)
    used = f"esfera equivalente {_fmt_d(equivalent_d)} D" if cylinder_d else f"{_fmt_d(equivalent_d)} D"
    if magnitude > MAX_SPHERE_D:
        return _fail(*args, f"Fuera de tabla ({used}; máximo ±{MAX_SPHERE_D} D).")
    if magnitude < 1:
        return _fail(*args, f"La tabla no tiene datos por debajo de ±1 D ({used}).")

    sign = 1 if equivalent_d > 0 else -1
    low, high = math.floor(magnitude), math.ceil(magnitude)
    row_low = _BY_SPHERE[sign * low][zone]
    row_high = _BY_SPHERE[sign * high][zone]
    if row_low is None or row_high is None:
        return _fail(
            *args,
            f"Sin datos en la tabla para {used} con zona óptica {str(zone).replace('.', ',')} mm.",
        )

    if low == high:
        time_s, ablation_um, zone_mm = row_low
        return LaserAblation(
            True, sphere_d, cylinder_d, equivalent_d, zone, ablation_um, time_s, zone_mm, False
        )

    fraction = magnitude - low
    ablation_um = math.ceil(row_low[1] + (row_high[1] - row_low[1]) * fraction)
    return LaserAblation(True, sphere_d, cylinder_d, equivalent_d, zone, ablation_um, None, "", True)
