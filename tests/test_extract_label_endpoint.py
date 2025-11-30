import io
from fastapi.testclient import TestClient
from troostwatch.app.api import app


def test_extract_label_endpoint():
    client = TestClient(app)
    # Use a small valid PNG image (blank, for test)
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\x0b\x0e\x00\x00\x00\x00IEND\xaeB`\x82"
    response = client.post(
        "/extract-label",
        files={"file": ("test.png", io.BytesIO(png_bytes), "image/png")},
        data={"ocr_language": "eng"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert "label" in data
    assert "preprocessing_steps" in data
    assert "ocr_confidence" in data
