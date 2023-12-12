import glob
import gzip

from fastapi import APIRouter, status, HTTPException
from pandas import read_json

from bdi_api.settings import Settings

import requests
import os
from pathlib import Path
import pandas as pd
import json
import shutil

settings = Settings()

BASE_URL = "https://samples.adsbexchange.com/readsb-hist/2023/11/01/"

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
    download_dir = Path(settings.raw_dir) / "day=20231101"
    download_dir.mkdir(parents=True, exist_ok=True)

    for i in range(0, 1000):  # Adjusted the range to increment by 5
        file_name = f"{i:06}Z.json.gz"
        file_url = f"{BASE_URL}{file_name}"
        file_path = download_dir / file_name

        # Download the .gz file
        try:
            response = requests.get(file_url)
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                f.write(response.content)

            # Now, you may want to decompress it right away
            with gzip.open(file_path, 'rb') as f_in:
                with open(file_path.with_suffix(''), 'wb') as f_out:  # Removes the .gz suffix
                    shutil.copyfileobj(f_in, f_out)

            # Deletes the original .gz file after decompression
            file_path.unlink()

        except requests.HTTPError as http_err:
            if http_err.response.status_code == 404:
                # Silently ignore 404 errors and continue with the next iteration
                continue
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"An error occurred: {err}")

    return "OK"
    # data_dir = Path(settings.raw_dir) / "day=20231101"
    # if not data_dir.exists():
    #     return "Data directory does not exist."
    #
    # # Initialize an empty DataFrame to hold all the data
    # all_data = pd.DataFrame()
    #
    # # Process each JSON file
    # for json_file in data_dir.glob('*.json'):
    #     # Read the file into a DataFrame
    #     df = pd.read_json(json_file)
    #     # Append to the all_data DataFrame
    #     all_data = all_data.append(df, ignore_index=True)


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
    download_dir = Path(settings.raw_dir) / "day=20231101" / "prepared"  # Updated path to the prepared directory
    output_dir = Path(settings.prepared_dir) / "day=20231101"  # Directory to store the processed files
    print(f"Download Directory: {download_dir}")
    print(f"Output Directory: {output_dir}")
    # Ensure the output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory exists: {output_dir.exists()}")

    # Process each file
    # Process each file
    filenames = glob.glob(f'{download_dir}/*.json')
    print(f"Found {len(filenames)} files to process")

    for filename in filenames:
        print(f"Processing file: {filename}")
        try:
            with open(filename, 'r') as file:  # Open the JSON file
                data = json.load(file)

            aircraft_data = data.get("aircraft", [])
            timestamp = data.get("now", "")

            extracted_data = []
            for aircraft in aircraft_data:
                extracted_data.append({
                    "icao": aircraft.get("hex", ""),
                    "registration": aircraft.get("r", ""),
                    "type": aircraft.get("t", ""),
                    "flight_name": aircraft.get("flight", "").strip(),  # Remove trailing spaces
                    "altitude_baro": aircraft.get("alt_baro", ""),
                    "ground_speed": aircraft.get("gs", ""),
                    "latitude": aircraft.get("lat", ""),
                    "longitude": aircraft.get("lon", ""),
                    "flight_status": aircraft.get("alert", ""),
                    "emergency": aircraft.get("emergency", ""),
                    "timestamp": timestamp
                })

            # Write to a new file in the output directory
            output_filename = os.path.join(output_dir, f'{Path(filename).stem}.processed.json')
            with open(output_filename, 'w') as output_file:
                json.dump(extracted_data, output_file, indent=4)

        except Exception as e:
            print(f"An error occurred while processing {filename}: {e}")

    return "OK"
    # data_dir = Path(settings.raw_dir) / "day=20231101"
    # prepared_dir = data_dir / "prepared"
    # local_data = Path(settings.local_dir)


    # Clean the prepared directory
    # if prepared_dir.exists():
    #     shutil.rmtree(prepared_dir)
    # prepared_dir.mkdir()
    #
    # # Initialize an empty DataFrame to store all data
    # dataframe_total = pd.DataFrame()
    #
    # # Read and process each JSON file
    # for json_file in local_data.glob('*.json'):
    #     df = pd.read_json(json_file)
    #     df = df['aircraft']
    #     df = pd.DataFrame([[k, *v] for k, v in df.items()],
    #                       columns=['hex', 'type', 'flight' 'r', 't', 'alt_baro', 'gs', 'lat', 'lon', 'alt_baro', 'gs', 'emergency'])
    #     #print(df.info())
    #    # "hex": "a65800", "type": "adsc", "flight": "DL295   ", "r": "N508DN", "t": "A359", "alt_baro": 39996, "gs": 454.0, "track": 244.71, "baro_rate": -16, "lat": 46.577740, "lon": -178.413162, "nic": 0, "rc": 0, "seen_pos": 190.091, "alert": 0, "spi": 0, "mlat": [], "tisb": [], "messages": 31181264, "seen": 190.1, "rssi": -49.5
    #
    #     # Select only the required columns
    #   #  df = df[['hex', 'r', 't', 'lat', 'lon', 'alt_baro', 'gs', 'emergency']]
    #
    #     # Rename columns to desired names
    #     df.rename(columns={
    #         'hex': 'icao',
    #         'r': 'registration',
    #         't': 'type',
    #         'lat': 'lat',
    #         'lon': 'lon',
    #         'alt_baro': 'altitude_baro',
    #         'gs': 'ground_speed',
    #     }, inplace=True)
    #     print(df)
    #     return "OK"
    #
    #     # Create "had_emergency" column
    #     df["had_emergency"] = df["emergency"].apply(lambda e: e not in ["none", None])
    #
    #     # Convert "now" column to datetime and assign it to "timestamp" column
    #     df["timestamp"] = pd.to_datetime(df["timestamp"], unit='s')
    #
    #     # Append the processed DataFrame to the total DataFrame
    #     dataframe_total = pd.concat([dataframe_total, df], ignore_index=True)
    #     print(dataframe_total)
    #     print("hello world")
    #     # Partition by aircraft type
    #     for aircraft_type, group in dataframe_total.groupby('type'):
    #         type_dir = prepared_dir / str(aircraft_type)
    #         type_dir.mkdir(parents=True, exist_ok=True)
    #         group.to_csv(type_dir / f"{json_file.stem}_prepared.csv", index=False)

    #return "OK"


@s1.get("/aircraft/")
def list_aircraft(num_results: int = 100, page: int = 0) -> list[dict]:
    """List all the available aircraft, its registration and type ordered by
    icao asc
    """
    # TODO
    prepared_dir = Path(settings.raw_dir) / "day=20231101/prepared"

    # Check if the directory exists
    if prepared_dir.exists() and prepared_dir.is_dir():
        # List CSV files in the directory
        csv_files = list(prepared_dir.glob("*.csv"))

        # Print the list of CSV files
        for csv_file in csv_files:
            print(csv_file.name)
    else:
        print("The 'prepared' directory does not exist.")

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
