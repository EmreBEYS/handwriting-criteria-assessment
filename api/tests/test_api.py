from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_reports_model_as_not_ready() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["model_ready"] is False
    assert response.headers["X-Request-ID"]


def test_analysis_rejects_non_image_upload() -> None:
    response = client.post("/v1/analyses", files={"image": ("note.txt", b"text", "text/plain")})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MEDIA_TYPE"


def test_analysis_stays_disabled_before_model_decision() -> None:
    response = client.post("/v1/analyses", files={"image": ("sample.png", b"png", "image/png")})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MODEL_NOT_CONFIGURED"
