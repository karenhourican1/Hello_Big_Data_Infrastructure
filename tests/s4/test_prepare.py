# test code sourced from ChatGPT
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient
from unittest.mock import patch
import pytest
from bdi_api.app import app

client = TestClient(app)


def test_prepare_success():
    with patch('bdi_api.s4.exercise.boto3.client') as mock_s3_client:
        # Configure the mock S3 client here
        mock_s3_client.return_value.list_objects_v2.return_value = {
            'Contents': [{'Key': 'somekey'}]
        }
        mock_s3_client.return_value.download_file.return_value = None

        response = client.post("/api/s4/aircraft/prepare")
        assert response.status_code == 200


def test_prepare_s3_error():
    with patch('bdi_api.s4.exercise.boto3.client') as mock_s3_client:
        # Configure the mock S3 client to raise an exception
        mock_s3_client.return_value.list_objects_v2.side_effect = ClientError(
            {"Error": {"Code": "MockedError", "Message": "Mocked exception"}},
            "list_objects_v2"
        )

        response = client.post
