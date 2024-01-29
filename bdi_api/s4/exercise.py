import boto3

from botocore.exceptions import ClientError
from fastapi import APIRouter, status, HTTPException
from bdi_api.settings import Settings

import requests
from pathlib import Path
import json
from bs4 import BeautifulSoup

import logging
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

settings = Settings()
BASE_URL = "https://samples.adsbexchange.com/readsb-hist/2023/11/01/"

s4 = APIRouter(
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Something is wrong with the request"},
    },
    prefix="/api/s4",
    tags=["s4"],
)


@s4.post("/aircraft/download")
def download_data() -> str:
    """ Same as s1 but store to an aws s3 bucket taken from settings
    and inside the path `raw/day=20231101/`

    NOTE: you can change that value via the environment variable `BDI_S3_BUCKET`
    """
    # BASE_URL
    s3_bucket = settings.s3_bucket
    s3_prefix_path = "raw/day=20231101/"
    s3_client = boto3.client('s3')

    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        file_list = [a['href'] for a in soup.find_all('a') if a['href'].endswith('Z.json.gz')]

        for file_name in file_list[:1000]:  # Limit to the first 1000 files
            file_url = f"{BASE_URL}{file_name}"
            response = requests.get(file_url)
            response.raise_for_status()

            s3_client.put_object(
                Bucket=s3_bucket,
                Key=f"{s3_prefix_path}{file_name}",
                Body=response.content
            )

        return "OK"

    except (ClientError, BotoCoreError) as e:
        logger.error(f"Error occurred during S3 operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


@s4.post("/aircraft/prepare")
def prepare_data() -> str:
    """Obtain the data from AWS s3 and store it in the local `prepared` directory
    as done in s2.

    All the `/api/s1/aircraft/` endpoints should work as usual
    """
    s3_client = boto3.client('s3')
    s3_bucket = settings.s3_bucket
    s3_prefix_path = "raw/day=20231101/"
    prepared_dir = Path(settings.prepared_dir) / "day=20231101"
    prepared_dir.mkdir(parents=True, exist_ok=True)

    try:
        # List files in the S3 bucket
        objects = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=s3_prefix_path)

        for obj in objects.get('Contents', []):
            file_name = obj['Key'].split('/')[-1]
            file_path = prepared_dir / file_name

            # Download file from S3
            s3_client.download_file(s3_bucket, obj['Key'], str(file_path))

            # Process each file
            with open(file_path, 'r') as file:
                data = json.load(file)
            aircraft_data = data.get("aircraft", [])
            timestamp = data.get("now", "")

            # Extract required fields into a list of dictionaries
            extracted_data = []
            for aircraft in aircraft_data:
                extracted_data.append({
                    "icao": aircraft.get("hex", ""),
                    "registration": aircraft.get("r", ""),
                    "type": aircraft.get("t", ""),
                    "flight_name": aircraft.get("flight", "").strip(),
                    "altitude_baro": aircraft.get("alt_baro", ""),
                    "ground_speed": aircraft.get("gs", ""),
                    "latitude": aircraft.get("lat", ""),
                    "longitude": aircraft.get("lon", ""),
                    "flight_status": aircraft.get("alert", ""),
                    "emergency": aircraft.get("emergency", ""),
                    "timestamp": timestamp
                })

            # Write the processed data to a new file in the prepared directory
            output_filename = prepared_dir / f'{Path(file_name).stem}.processed.json'
            with open(output_filename, 'w') as output_file:
                json.dump(extracted_data, output_file, indent=4)

        return "OK"

    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
