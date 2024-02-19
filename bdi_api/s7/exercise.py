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
from typing import List, Dict, Any

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
                # Validation and conversion for max_altitude_baro
                try:
                    max_altitude_baro = int(record.get('alt_baro', 0))
                except (ValueError, TypeError):
                    max_altitude_baro = None
                # Validation and conversion for max_ground_speed
                try:
                    max_ground_speed = float(record.get('gs', 0.0))
                except (ValueError, TypeError):
                    max_ground_speed = None  # Assign a default value or None

                # Check if aircraft exists and create if not
                aircraft = db.query(Aircraft).filter_by(icao=record['hex']).first()
                if not aircraft:
                    aircraft = Aircraft(
                        icao=record['hex'],
                        registration=record.get('r'),
                        type=record.get('t')
                    )
                    db.add(aircraft)
                    db.flush()  # Flush to assign an ID to the new aircraft object

                # Create new position entry
                new_position = Position(
                    aircraft_id=aircraft.aircraft_id,
                    timestamp=json_data['now'],
                    latitude=record.get('lat'),
                    longitude=record.get('lon')
                )
                db.add(new_position)

                # Create new statistic entry only if max_altitude_baro is valid
                if max_altitude_baro is not None:
                    new_statistic = Statistic(
                        aircraft_id=aircraft.aircraft_id,
                        max_altitude_baro=max_altitude_baro,
                        max_ground_speed=max_ground_speed,
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


@s7.get("/aircraft/", response_model=List)
def list_aircraft(db: Session = Depends(get_db)) -> List[Dict[str, str]]:
    """List all the available aircraft, its registration and type ordered by
    icao asc FROM THE DATABASE

    Use credentials passed from `db_credentials`
    """
    aircraft_query = db.query(Aircraft).order_by(Aircraft.icao.asc()).all()
    if not aircraft_query:
        raise HTTPException(status_code=404, detail="No aircraft found")
    # Transform SQLAlchemy model instances into dictionaries for response
    return [{"icao": aircraft.icao, "registration": aircraft.registration, "type": aircraft.type} for aircraft in aircraft_query]


@s7.get("/aircraft/{icao}/positions", response_model=List[Dict[str, float]])
def get_aircraft_position(icao: str, num_results: int = 1000, page: int = 0, db: Session = Depends(get_db)) -> List[Dict[str, float]]:
    """Returns all the known positions of an aircraft ordered by time (asc)
    If an aircraft is not found, return an empty list. FROM THE DATABASE

    Use credentials passed from `db_credentials`
    """
    # Query the database for the aircraft with the given icao code
    aircraft = db.query(Aircraft).filter(Aircraft.icao == icao).first()
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    # Query the positions for the given aircraft, ordered by timestamp
    position_query = (db.query(Position)
                      .filter(Position.aircraft_id == aircraft.aircraft_id)
                      .order_by(Position.timestamp.asc())
                      .offset(page * num_results)
                      .limit(num_results)
                      .all())

    # If no positions found, return an empty list
    if not position_query:
        return []

    # Transform SQLAlchemy position objects into dictionaries
    positions = [{"timestamp": pos.timestamp, "lat": pos.latitude, "lon": pos.longitude} for pos in position_query]
    return positions


@s7.get("/aircraft/{icao}/stats", response_model=Dict[str, float])
def get_aircraft_statistics(icao: str, db: Session = Depends(get_db)) -> dict[str, str] | dict[str, Any]:
    """Returns different statistics about the aircraft

    * max_altitude_baro
    * max_ground_speed
    * had_emergency

    FROM THE DATABASE

    Use credentials passed from `db_credentials`
    """
    # Find the aircraft by icao code to ensure it exists
    aircraft = db.query(Aircraft).filter(Aircraft.icao == icao).first()
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    # Query the statistics for the aircraft
    stats = db.query(Statistic).filter(Statistic.aircraft_id == aircraft.aircraft_id).all()

    if not stats:
        return {"message": "No stats found for this aircraft"}

    stat = stats
    return {
        "max_altitude_baro": stat.max_altitude_baro,
        "max_ground_speed": stat.max_ground_speed,
        "had_emergency": stat.had_emergency
    }