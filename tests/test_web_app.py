from fastapi.testclient import TestClient

from web_app.app import app


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
            "legacy_mode": False,
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
    assert "Usar online" in response.text
