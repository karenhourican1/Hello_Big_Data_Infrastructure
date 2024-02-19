import logging

import boto3
import gzip
import json

from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from bdi_api.settings import DBCredentials, Settings

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import text, create_engine

from bdi_api.models import Aircraft, Position, Statistic

logger = logging.getLogger("uvicorn.error")

settings = Settings()
db_credentials = DBCredentials()
BASE_URL = "https://samples.adsbexchange.com/readsb-hist/2023/11/01/"

# Construct the database URL from credentials
DATABASE_URL = f"postgresql://{db_credentials.username}:{db_credentials.password}@{db_credentials.host}:{db_credentials.port}/{db_credentials.dbname}"

# Create the SQLAlchemy engine and sessionmaker
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define S3 bucket and key prefix
bucket_name = settings.s3_bucket
prefix = 'raw/day=20231101/'


# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


s7 = APIRouter(
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Something is wrong with the request"},
    },
    prefix="/api/s7",
    tags=["s7"],
)


@s7.post("/aircraft/prepare")
def prepare_data(db: Session = Depends(get_db)) -> str:
    """Get the raw data from s3 and insert it into RDS

    Use credentials passed from `db_credentials`
    """
    user = db_credentials.username
    s3_client = boto3.client('s3')

    try:
        # # Log the start of the function
        logger.info("Starting data preparation")

        # Get the list of files from S3
        s3_objects = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if not s3_objects.get('Contents'):
            logger.warning(f"No files found in S3 bucket '{bucket_name}' with prefix '{prefix}'")
            return "No files found in S3 bucket."

        for obj in s3_objects.get('Contents', []):
            file_key = obj['Key']
            logger.info(f"Processing file: {file_key}")
            s3_object = s3_client.get_object(Bucket=bucket_name, Key=file_key)
            file_content = s3_object['Body'].read()

            # Check if the file is empty
            if s3_object['ContentLength'] == 0:
                logger.warning(f"Found an empty file: {file_key}")
                continue

            # Log the type of the object's body
            logger.info(f"Type of s3_object['Body']: {type(s3_object['Body'])}")

            try:
                # Try to read as a gzipped file
                with gzip.GzipFile(fileobj=file_content) as gzipfile:
                    json_data = json.load(gzipfile)
            except gzip.BadGzipFile:
                # If not gzipped, treat as plain JSON
                json_data = json.loads(file_content)
                # Log the success of reading the file
                logger.info(f"Successfully read and decompressed the file: {file_key}")

                # Process each record and create database entries
                for record in json_data['aircraft']:
                    aircraft = db.query(Aircraft).filter_by(icao=record['hex']).first()
                    if not aircraft:
                        aircraft = Aircraft(
                            icao=record['hex'],
                            registration=record.get('r'),
                            type=record.get('t')
                        )
                        db.add(aircraft)

                    new_position = Position(
                        aircraft_id=aircraft.id,
                        timestamp=json_data['now'],
                        latitude=record.get('lat'),
                        longitude=record.get('lon')
                    )
                    db.add(new_position)

                    new_statistic = Statistic(
                        aircraft_id=aircraft.id,
                        timestamp=json_data['now'],
                        max_altitude_baro=record.get('alt_baro'),
                        max_ground_speed=record.get('gs'),
                        had_emergency=bool(record.get('alert'))
                    )
                    db.add(new_statistic)

                # Commit the session to save all the new records to the database
                db.commit()

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except boto3.exceptions.Boto3Error as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    return "OK"


@s7.get("/aircraft/")
def list_aircraft(num_results: int = 100, page: int = 0) -> list[dict]:
    """List all the available aircraft, its registration and type ordered by
    icao asc FROM THE DATABASE

    Use credentials passed from `db_credentials`
    """
    # TODO
    return [{"icao": "0d8300", "registration": "YV3382", "type": "LJ31"}]


@s7.get("/aircraft/{icao}/positions")
def get_aircraft_position(icao: str, num_results: int = 1000, page: int = 0) -> list[dict]:
    """Returns all the known positions of an aircraft ordered by time (asc)
    If an aircraft is not found, return an empty list. FROM THE DATABASE

    Use credentials passed from `db_credentials`
    """
    # TODO
    return [{"timestamp": 1609275898.6, "lat": 30.404617, "lon": -86.476566}]


@s7.get("/aircraft/{icao}/stats")
def get_aircraft_statistics(icao: str) -> dict:
    """Returns different statistics about the aircraft

    * max_altitude_baro
    * max_ground_speed
    * had_emergency

    FROM THE DATABASE

    Use credentials passed from `db_credentials`
    """
    # TODO
    return {"max_altitude_baro": 300000, "max_ground_speed": 493, "had_emergency": False}
