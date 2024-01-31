# Test code sourced from chatGPT

from fastapi.testclient import TestClient
from unittest.mock import patch
import pytest

from bdi_api.app import app  # Ensure this import matches your project structure

client = TestClient(app)


def test_download_success():
    response = client.post("/api/s4/aircraft/download")
    assert response.status_code == 200


@patch('bdi_api.s4.exercise.requests.get')
def test_download_error_handling(mock_get):
    # Configure the mock to raise an exception when called
    mock_get.side_effect = Exception("Connection error")

    with pytest.raises(Exception) as excinfo:
        client.post("/api/s4/aircraft/download")

    assert "Connection error" in str(excinfo.value)
