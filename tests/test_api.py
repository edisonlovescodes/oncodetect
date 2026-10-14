import hashlib
import io
import numpy as np
from PIL import Image
import pytest
from fastapi.testclient import TestClient
from backend.main import create_app


class FixedModel:
    def predict(self, image, verbose=0):
        assert image.shape == (1, 224, 224, 3)
        return np.array([[0.75]])


def png():
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def client(tmp_path):
    artifact = tmp_path / "model.h5"
    artifact.write_bytes(b"test fixture, not a trained model")
    app = create_app(
        model_path=artifact,
        database_url=f'sqlite:///{tmp_path / "test.db"}',
        model_loader=lambda _: FixedModel(),
    )
    with TestClient(app) as c:
        yield c


def test_prediction_is_persisted_without_fake_explanation(client):
    assert client.get("/api/stats").json()["total_predictions"] == 0
    r = client.post("/api/predict", files={"file": ("crop.png", png(), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["prediction"] == "Malignant"
    assert body["confidence"] == 75
    assert body["timestamp"].endswith("+00:00")
    assert "heatmap_url" not in body
    assert body["model_sha256"] == hashlib.sha256(b"test fixture, not a trained model").hexdigest()
    records = client.get("/api/predictions").json()
    assert records["count"] == 1
    assert records["predictions"][0]["id"] == body["prediction_id"]
    assert client.get("/api/stats").json()["malignant_count"] == 1


@pytest.mark.parametrize(
    "filename,data,mime",
    [
        ("bad.txt", b"bad", "text/plain"),
        ("bad.png", b"bad", "image/png"),
        ("empty.png", b"", "image/png"),
    ],
)
def test_invalid_images_are_400_not_500(client, filename, data, mime):
    assert client.post("/api/predict", files={"file": (filename, data, mime)}).status_code == 400
    assert client.get("/api/stats").json()["total_predictions"] == 0


def test_size_limit(client):
    r = client.post(
        "/api/predict", files={"file": ("huge.png", b"x" * (8 * 1024 * 1024 + 1), "image/png")}
    )
    assert r.status_code == 413


@pytest.mark.parametrize("limit", [0, -1, 101])
def test_history_bound(client, limit):
    assert client.get(f"/api/predictions?limit={limit}").status_code == 422


def test_missing_model_is_not_ready(tmp_path):
    app = create_app(
        model_path=tmp_path / "missing.h5", database_url=f'sqlite:///{tmp_path / "test.db"}'
    )
    with TestClient(app) as c:
        assert c.get("/api/health").status_code == 503
        assert c.get("/api/health").json()["model_loaded"] is False
        assert (
            c.post("/api/predict", files={"file": ("crop.png", png(), "image/png")}).status_code
            == 503
        )
        assert c.get("/api/predictions").json()["count"] == 0


def test_inference_failure_does_not_write_prediction(client):
    client.app.state.model.predict = lambda *a, **k: np.array([[float("nan")]])
    r = client.post("/api/predict", files={"file": ("crop.png", png(), "image/png")})
    assert r.status_code == 500
    assert client.get("/api/stats").json()["total_predictions"] == 0
