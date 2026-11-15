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
    assert [item["value"] for item in payload["procedure_choices"]] == ["lasik", "prk"]


def post(**body):
    return client.post("/api/compute", json={"paqui_preop_um": 540, **body}).json()


def test_compute_lasik_with_direct_ablation_subtracts_flap():
    payload = post(ablation_um=80, procedure="lasik")

    assert payload["valid"] is True
    assert payload["subtract_um"] == 120
    assert payload["ler_um"] == 340


def test_compute_prk_does_not_subtract_flap():
    payload = post(ablation_um=80, procedure="prk")

    assert payload["subtract_um"] == 0
    assert payload["ler_um"] == 460


def test_compute_from_graduation_uses_the_teneo_table():
    payload = post(sphere_d=-3, optical_zone_mm=6.5, procedure="lasik")

    assert payload["ablation_um"] == 52
    assert payload["laser"]["zone_mm"] == "7.8 x 7.8"
    assert payload["ler_um"] == 540 - 120 - 52


def test_compute_from_graduation_with_cylinder():
    payload = post(sphere_d=-3, cylinder_d=-2, optical_zone_mm=6.0, procedure="prk")

    assert payload["laser"]["equivalent_d"] == -4
    assert payload["ablation_um"] == 57


def test_compute_reports_missing_table_data():
    payload = post(sphere_d=9, optical_zone_mm=6.5)

    assert payload["valid"] is False
    assert "Sin datos" in payload["errors"][0]


def test_compute_needs_graduation_or_ablation():
    payload = post()

    assert payload["valid"] is False


def test_smile_and_surface_are_no_longer_accepted():
    assert client.post("/api/compute", json={"paqui_preop_um": 540, "ablation_um": 80, "procedure": "smile"}).status_code == 422
    assert client.post("/api/compute", json={"paqui_preop_um": 540, "ablation_um": 80, "procedure": "surface"}).status_code == 422


def test_index_serves_web_app():
    response = client.get("/")

    assert response.status_code == 200
    assert "AblacionCorneal" in response.text
    assert "Calculadora clínica" in response.text
    assert "Descargar app Mac" in response.text


def test_web_ui_has_no_legacy_smile_or_flap_field():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8").lower()
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8").lower()

    for text in (html, js):
        assert "legacy" not in text
        assert "smile" not in text
    assert "flap-cap-input" not in html
    assert 'id="optical-zone-select"' in html
    assert 'id="sphere-input"' in html
    assert 'id="cylinder-input"' in html


def test_config_exposes_defaults():
    data = client.get("/api/config").json()

    assert data["default_procedure"] == "lasik"
    assert data["flap_um"] == 120
    assert data["optical_zone_choices"] == [6.0, 6.5]
    assert data["default_optical_zone_mm"] == 6.0


def test_index_references_versioned_assets_and_is_not_cached():
    response = client.get("/")

    assert "__ASSET_VERSION__" not in response.text
    assert "/static/app.js?v=" in response.text
    assert "/static/app.css?v=" in response.text
    assert response.headers["cache-control"] == "no-cache"


def test_static_files_must_be_revalidated():
    for path in ("/static/app.js", "/static/app.css"):
        assert client.get(path).headers["cache-control"] == "no-cache"


def test_favicon_is_linked_and_served():
    html = client.get("/").text
    assert 'rel="icon"' in html and "/assets/favicon.svg" in html
    assert "/assets/apple-touch-icon.png" in html

    ico = client.get("/favicon.ico")
    assert ico.status_code == 200
    assert ico.headers["content-type"] == "image/x-icon"
    assert ico.content[:4] == b"\x00\x00\x01\x00"  # cabecera ICO válida

    for path in ("/assets/favicon.svg", "/assets/favicon-32.png", "/assets/apple-touch-icon.png"):
        assert client.get(path).status_code == 200
