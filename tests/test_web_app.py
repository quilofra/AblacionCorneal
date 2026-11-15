from fastapi.testclient import TestClient

from web_app.app import STATIC_DIR, app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_config_endpoint_exposes_procedures():
    response = client.get("/api/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["app_name"] == "AblacionCorneal"
    assert [item["value"] for item in payload["procedure_choices"]] == [
        "surface",
        "lasik",
        "smile",
    ]


def test_compute_endpoint_uses_shared_calculator():
    response = client.post(
        "/api/compute",
        json={
            "paqui_preop_um": 500,
            "ablation_um": 80,
            "suspicious": False,
            "procedure": "lasik",
            "flap_cap_um": 110,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["subtract_um"] == 110
    assert payload["ler_um"] == 310
    assert payload["overall_status"] == "warning"


def test_index_serves_web_app():
    response = client.get("/")

    assert response.status_code == 200
    assert "AblacionCorneal" in response.text
    assert "Calculadora clínica" in response.text
    assert "Descargar app Mac" in response.text


def test_web_ui_has_no_legacy_toggle_and_defaults_flap():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert "legacy" not in html.lower()
    assert 'value="120"' in html


def test_old_clients_sending_legacy_mode_still_get_flap_subtracted():
    response = client.post(
        "/api/compute",
        json={"paqui_preop_um": 540, "ablation_um": 80, "procedure": "lasik", "flap_cap_um": 120, "legacy_mode": True},
    )
    assert response.json()["ler_um"] == 340


def test_config_exposes_flap_defaults():
    data = client.get("/api/config").json()
    assert data["default_flap_cap_um"] == 120
    assert data["default_procedure"] == "lasik"


def test_laser_ablation_endpoint_returns_table_value():
    payload = client.get("/api/laser-ablation", params={"sphere_d": -3, "optical_zone_mm": 6.5}).json()

    assert payload["found"] is True
    assert payload["ablation_um"] == 52
    assert payload["zone_mm"] == "7.8 x 7.8"


def test_laser_ablation_endpoint_reports_missing_data():
    payload = client.get("/api/laser-ablation", params={"sphere_d": 9, "optical_zone_mm": 6.5}).json()

    assert payload["found"] is False
    assert "Sin datos" in payload["message"]


def test_config_exposes_optical_zones():
    data = client.get("/api/config").json()

    assert data["optical_zone_choices"] == [6.0, 6.5]
    assert data["default_optical_zone_mm"] == 6.0
