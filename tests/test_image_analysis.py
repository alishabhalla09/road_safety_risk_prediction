import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.image_analysis_service import ImageAnalysisService

client = TestClient(app)


def test_image_analysis_service_synthetic():
    result = ImageAnalysisService.analyze_image()
    assert result["status"] == "SUCCESS"
    assert result["risk_score"] >= 70.0
    assert result["risk_category"] == "HIGH"
    assert result["violation"]["type"] == "WRONG_WAY_HEAD_ON"
    assert "violator_plate" in result["anpr"]
    assert result["challan"]["fine_amount"] == 5000
    assert result["annotated_image"].startswith("data:image/jpeg;base64,")


def test_image_analysis_api_endpoint(db_session):
    response = client.post("/analysis/image")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["risk_score"] >= 70.0
    assert data["challan"]["fine_amount"] == 5000
