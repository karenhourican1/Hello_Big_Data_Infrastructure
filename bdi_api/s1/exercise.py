from fastapi import APIRouter, status, HTTPException

from bdi_api.settings import Settings

import requests
import os
from pathlib import Path
import pandas as pd
import shutil

settings = Settings()

#BASE_URL = "https://samples.adsbexchange.com/readsb-hist/2023/11/01/"

s1 = APIRouter(
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Something is wrong with the request"},
    },
    prefix="/api/s1",
    tags=["s1"],
)


@s1.post("/aircraft/download")
def download_data() -> str:
    """Downloads the **first 1000** files AS IS inside the folder data/20231101

    data: https://samples.adsbexchange.com/readsb-hist/2023/11/01/
    documentation: https://www.adsbexchange.com/version-2-api-wip/
        See "Trace File Fields" section

    Think about the way you organize the information inside the folder
    and the level of preprocessing you might need.

    To manipulate the data use any library you feel comfortable with.
    Just make sure to configure it in the `pyproject.toml` file
    so it can be installed using `poetry update`.
    """
    # TODO
    # download_dir = os.path.join(settings.raw_dir, "day=20231101")
    # BASE_URL
    """
        Process the JSON files that are already downloaded and stored in the folder data/raw
        """
    data_dir = Path(settings.raw_dir) / "day=20231101"
    if not data_dir.exists():
        return "Data directory does not exist."

    # Initialize an empty DataFrame to hold all the data
    all_data = pd.DataFrame()

    # Process each JSON file
    for json_file in data_dir.glob('*.json'):
        # Read the file into a DataFrame
        df = pd.read_json(json_file)
        # Append to the all_data DataFrame
        all_data = all_data.append(df, ignore_index=True)

    return "OK"


@s1.post("/aircraft/prepare")
def prepare_data() -> str:
    """Prepare the data in the way you think it's better for the analysis.

    * data: https://samples.adsbexchange.com/readsb-hist/2023/11/01/
    * documentation: https://www.adsbexchange.com/version-2-api-wip/
        See "Trace File Fields" section

    Think about the way you organize the information inside the folder
    and the level of preprocessing you might need.

    To manipulate the data use any library you feel comfortable with.
    Just make sure to configure it in the `pyproject.toml` file
    so it can be installed using `poetry update`.

    TIP: always clean the prepared folder before writing again to avoid having old
    data
    """
    # TODO
    data_dir = Path(settings.raw_dir) / "day=20231101"
    prepared_dir = data_dir / "prepared"

    # Clean the prepared directory
    if prepared_dir.exists():
        shutil.rmtree(prepared_dir)
    prepared_dir.mkdir(parents=True, exist_ok=True)

    # Initialize an empty DataFrame to hold all the data
    dataframe_total = pd.DataFrame()

    # Read and process each JSON file
    for json_file in data_dir.glob('*.json'):
        df = pd.read_json(json_file)

        # Rename columns
        df.rename(
            columns={
                "hex": "icao",
                "r": "registration",
                "type": "messages_type",
                "t": "type",
                "alt_baro": "altitude_baro",
                "gs": "ground_speed"
            }, inplace=True)

        # Add 'had_emergency' column
        df["had_emergency"] = df["emergency"].apply(lambda e: e not in ["none", None])

        # Convert 'now' column to datetime
        df["timestamp"] = pd.to_datetime(df["now"], unit='s')

        # Append to the total DataFrame
        dataframe_total = dataframe_total.append(df, ignore_index=True)

    # Partition by aircraft type and save
    for aircraft_type, group in dataframe_total.groupby('type'):
        type_dir = prepared_dir / str(aircraft_type)
        type_dir.mkdir(parents=True, exist_ok=True)
        group.to_csv(type_dir / f"{str(aircraft_type)}_prepared.csv", index=False)

    return "OK"



@s1.get("/aircraft/")
def list_aircraft(num_results: int = 100, page: int = 0) -> list[dict]:
    """List all the available aircraft, its registration and type ordered by
    icao asc
    """
    # TODO
    prepared_dir = Path(settings.raw_dir) / "day=20231101/prepared"

    # Check if the prepared directory exists
    if not prepared_dir.exists():
        raise HTTPException(status_code=404, detail="Prepared data not found")

    # Initialize an empty DataFrame to hold all aircraft data
    all_aircraft = pd.DataFrame()

    # Read prepared data from each type directory
    for type_dir in prepared_dir.iterdir():
        if type_dir.is_dir():  # Ensure it's a directory
            for file in type_dir.glob("*.csv"):
                df = pd.read_csv(file, usecols=["icao", "registration", "type"])
                all_aircraft = all_aircraft.append(df, ignore_index=True)

    # Print column names for debugging
    print(all_aircraft.columns)

    # Check if 'icao' column exists
    if 'icao' not in all_aircraft.columns:
        raise HTTPException(status_code=500, detail="'icao' column not found in data")
    # Sort by 'icao' in ascending order
    all_aircraft.sort_values(by="icao", inplace=True)

    # Implement pagination
    start = page * num_results
    end = start + num_results
    paginated_aircraft = all_aircraft.iloc[start:end]

    # Convert DataFrame to a list of dictionaries for output
    aircraft_list = paginated_aircraft.to_dict(orient="records")

    return aircraft_list


@s1.get("/aircraft/{icao}/positions")
def get_aircraft_position(icao: str, num_results: int = 1000, page: int = 0) -> list[dict]:
    """Returns all the known positions of an aircraft ordered by time (asc)
    If an aircraft is not found, return an empty list.
    """
    # TODO
    return [{"timestamp": 1609275898.6, "lat": 30.404617, "lon": -86.476566}]


@s1.get("/aircraft/{icao}/stats")
def get_aircraft_statistics(icao: str) -> dict:
    """Returns different statistics about the aircraft

    * max_altitude_baro
    * max_ground_speed
    * had_emergency
    """
    # TODO
    return {"max_altitude_baro": 300000, "max_ground_speed": 493, "had_emergency": False}
