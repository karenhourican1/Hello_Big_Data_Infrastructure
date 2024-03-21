import json
from typing import Optional, List
from datetime import datetime, timedelta

import boto3
from fastapi import APIRouter, status, Depends, HTTPException

from bdi_api.s8.dags.download_fuel_consumption_rates_dag import S3_BUCKET
from bdi_api.settings import Settings

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bdi_api.models import Aircraft, Position
from bdi_api.settings import DBCredentials
from pydantic import BaseModel

settings = Settings()
db_credentials = DBCredentials()
BASE_URL = "https://samples.adsbexchange.com/readsb-hist/2023/11/01/"

# Construct the database URL from credentials
DATABASE_URL = f"postgresql://{db_credentials.username}:{db_credentials.password}@{db_credentials.host}:{db_credentials.port}/{db_credentials.dbname}"

# Create the SQLAlchemy engine and sessionmaker
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


s8 = APIRouter(
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Something is wrong with the request"},
    },
    prefix="/api/s8",
    tags=["s8"],
)


# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AircraftReturn(BaseModel):
    # DO NOT MODIFY IT
    icao: str
    registration: Optional[str]
    type: Optional[str]
    owner: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]


@s8.get("/aircraft/", response_model=List[AircraftReturn])
def list_aircraft(db: Session = Depends(get_db), num_results: int = 100, page: int = 0) -> List[AircraftReturn]:
    """List all the available aircraft, its registration and type ordered by
        icao asc FROM THE DATABASE

        ADDITIONS:
        * Instead of passing a JSON, use pydantic to return the correct schema
           See: https://fastapi.tiangolo.com/tutorial/response-model/
        * Enrich it with information from the aircrafts database (see README for link)
          * `owner`  (`ownop` field in the aircrafts DB)
          * `manufacturer` and `model`


        IMPORTANT: Only return the aircraft that we have seen and not the entire list in the aircrafts database

"""

    query = (db.query(Aircraft)
             .order_by(Aircraft.icao)
             .limit(num_results)
             .offset(page * num_results))
    results = query.all()
    if not results:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    return [AircraftReturn(
                icao=aircraft.icao,
                registration=aircraft.registration,
                type=aircraft.type
            ) for aircraft in results]


class AircraftCO2(BaseModel):
    # DO NOT MODIFY IT
    icao: str
    hours_flown: float
    """Co2 tons generated"""
    co2: Optional[float]


@s8.get("/aircraft/{icao}/co2", response_model=AircraftCO2)
def get_aircraft_co2(icao: str, day: str, db: Session = Depends(get_db)) -> AircraftCO2:
    """Returns the CO2 generated by the aircraft **in a given day**.

    Compute the hours flown by the aircraft (assume each row we have is 5s).

    Then, you can use these metrics:

    ```python
    fuel_used_kg = fuel_used_gal * 3.04
	c02_tons = (fuel_used_kg * 3.15 ) / 907.185
	```

    Use the gallon per hour from https://github.com/martsec/flight_co2_analysis/blob/main/data/aircraft_type_fuel_consumption_rates.json
    The key is the `icaotype`

    ```json
    {
      ...,
      "GLF6": { "source":"https://github.com/Jxck-S/plane-notify",
        "name": "Gulfstream G650",
        "galph": 503,
        "category": "Ultra Long Range"
      },
    }

    If you don't have the fuel consumption rate, return `None` in the `co2` field
    ```
    """
    # Parse the input day in the format 'YYYY-MM-DD'
    try:
        day_to_compute = datetime.strptime(day, "%Y-%m-%d").date()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {day}. Expected format: YYYY-MM-DD.")

    # Retrieve the type of the aircraft using the icao from the database
    aircraft_type = db.query(Aircraft).filter(Aircraft.icao == icao).first()
    if not aircraft_type:
        raise HTTPException(status_code=404, detail=f"Aircraft with ICAO {icao} not found.")

    # Retrieve the fuel consumption rate for the aircraft's type
    fuel_consumption_rate = get_fuel_consumption_rate(aircraft_type.type)

    # If the fuel consumption rate is not available, return None for CO2
    if fuel_consumption_rate is None:
        return AircraftCO2(icao=icao, hours_flown=0, co2=None)

    # Calculate the hours flown from the number of position reports for that day
    # Assuming each position report represents 5 seconds of flight
    position_reports_count = db.query(Position).filter(
        Position.aircraft_id == aircraft_type.aircraft_id,
        Position.timestamp >= day_to_compute,
        Position.timestamp < day_to_compute + timedelta(days=1)
    ).count()
    hours_flown = (position_reports_count * 5) / 3600  # 5 seconds per position report

    # Calculate the fuel used in gallons
    fuel_used_gal = hours_flown * fuel_consumption_rate

    # Convert gallons to kg
    fuel_used_kg = fuel_used_gal * 3.04

    # Convert kg to tons and calculate CO2
    co2_tons = (fuel_used_kg * 3.15) / 907.185

    return AircraftCO2(icao=icao, hours_flown=hours_flown, co2=co2_tons)


def get_fuel_consumption_rate(icao_type: str) -> Optional[float]:
    s3_client = boto3.client('s3')
    try:
        file_name = f"fuel_consumption_rates_{datetime.now().strftime('%Y-%m')}.json"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=f"fuel_consumption/{file_name}")
        fuel_consumption_data = json.loads(response['Body'].read())
        rate_info = fuel_consumption_data.get(icao_type)
        if rate_info:
            return rate_info['galph']
    except s3_client.exceptions.NoSuchKey:
        print(f"The file {file_name} does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None
