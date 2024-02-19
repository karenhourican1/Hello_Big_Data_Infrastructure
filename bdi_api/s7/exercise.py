import logging
import boto3
import gzip
import json
import io

from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from bdi_api.settings import DBCredentials, Settings
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import text, create_engine
from bdi_api.models import Aircraft, Position, Statistic
from sqlalchemy import func
from typing import List, Dict

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
        s3_objects = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        for obj in s3_objects.get('Contents', []):
            file_key = obj['Key']
            s3_object = s3_client.get_object(Bucket=bucket_name, Key=file_key)
            file_content = s3_object['Body'].read()

            try:
                # Use io.BytesIO to create a file-like object from the bytes
                with gzip.GzipFile(fileobj=io.BytesIO(file_content)) as gzipfile:
                    json_data = json.load(gzipfile)
            except gzip.BadGzipFile:
                # If it's not gzipped, treat as plain JSON
                json_data = json.loads(file_content.decode('utf-8'))  # Decode bytes to string before loading as JSON

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
                    aircraft_id=aircraft.aircraft_id,
                    timestamp=json_data['now'],
                    # timestamp=13456.789,
                    latitude=record.get('lat'),
                    longitude=record.get('lon')
                )
                db.add(new_position)

                new_statistic = Statistic(
                    aircraft_id=aircraft.aircraft_id,
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


@s7.get("/aircraft/", response_model=List[Dict[str, str]])
def list_aircraft(num_results: int = 100, page: int = 0, db: Session = Depends(get_db)) -> List[Dict[str, str]]:
    """List all the available aircraft, its registration and type ordered by
    icao asc FROM THE DATABASE

    Use credentials passed from `db_credentials`
    """
    offset = page * num_results
    aircraft_query = db.query(Aircraft).order_by(Aircraft.icao.asc()).offset(offset).limit(num_results).all()

    aircraft_list = [{
        "icao": aircraft.icao,
        "registration": aircraft.registration,
        "type": aircraft.type
    } for aircraft in aircraft_query]

    if not aircraft_list:
        raise HTTPException(status_code=404, detail="No aircraft found")

    return aircraft_list


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
