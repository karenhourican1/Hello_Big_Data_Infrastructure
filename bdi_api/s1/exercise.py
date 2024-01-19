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
from bs4 import BeautifulSoup

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

    try:
        # Fetch file list
        response = requests.get(BASE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        file_list = [a['href'] for a in soup.find_all('a') if a['href'].endswith('Z.json.gz')]

        for file_name in file_list[:1000]:  # Limit to the first 1000 files
            file_url = f"{BASE_URL}{file_name}"
            file_path = download_dir / file_name

            try:
                # Download the .gz file
                file_response = requests.get(file_url)
                file_response.raise_for_status()

                with open(file_path, 'wb') as f:
                    f.write(file_response.content)

                # Decompress the files
                with gzip.open(file_path, 'rb') as f_in:
                    with open(file_path.with_suffix(''), 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Delete the original .gz file
                file_path.unlink()

            except requests.HTTPError as http_err:
                print(f"HTTP error occurred while downloading {file_name}: {http_err}")
            except Exception as err:
                print(f"An error occurred while downloading {file_name}: {err}")

    except requests.RequestException as e:
        print(f"Error fetching file list: {e}")
        return "Error"

    print("Download completed.")
    return "OK"

    # not_found_count = 0
    # error_count = 0

    # start_file = 905  # Starting from 000905Z.json.gz
    # end_file = 1000

    # for i in range(1000):
    #     file_name = f"{i:06}Z.json.gz"
    #     file_url = f"{BASE_URL}{file_name}"
    #     file_path = download_dir / file_name
    #
    #     print(f"Attempting to download file: {file_name}")  # Print the file number before the download attempt

        # # Download the .gz file
        # try:
        #     response = requests.get(file_url)
        #     response.raise_for_status()
        #
        #     with open(file_path, 'wb') as f:
        #         f.write(response.content)
        #
        #     # Decompress the files
        #     with gzip.open(file_path, 'rb') as f_in:
        #         with open(file_path.with_suffix(''), 'wb') as f_out:  # Removes the .gz suffix
        #             shutil.copyfileobj(f_in, f_out)
        #
        #     # Deletes the original .gz file after decompression
        #     file_path.unlink()

    #     except requests.HTTPError as http_err:
    #         if http_err.response.status_code == 404:
    #             not_found_count += 1
    #             # Silently ignore 404 errors and continue with the next iteration
    #             continue
    #         error_count += 1
    #         print(f"HTTP error occurred: {http_err}")
    #     except Exception as err:
    #         error_count += 1
    #         print(f"An error occurred: {err}")
    # print(f"Completed with {not_found_count} files not found and {error_count} other errors.")
    # return "OK"


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
    download_dir = os.path.join(settings.raw_dir, "day=20231101")
    prepared_dir = os.path.join(settings.prepared_dir,"day=20231101")

    # Create the prepared directory if it doesn't exist
    if not os.path.exists(prepared_dir):
        os.makedirs(prepared_dir, exist_ok=True)
        print("The prepared directory has been created")

    # Process each file
    filenames = glob.glob(f'{download_dir}/*.json')
    print(f"Found {len(filenames)} files to process")

    for filename in filenames:
        with open(filename, 'r') as file:
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
                "flight_name": aircraft.get("flight", "").strip(),  # Remove trailing spaces
                "altitude_baro": aircraft.get("alt_baro", ""),
                "ground_speed": aircraft.get("gs", ""),
                "latitude": aircraft.get("lat", ""),
                "longitude": aircraft.get("lon", ""),
                "flight_status": aircraft.get("alert", ""),
                "emergency": aircraft.get("emergency", ""),
                "timestamp": timestamp
            })
        # Write the processed data to a new file in the prepared directory
        output_filename = os.path.join(prepared_dir, f'{Path(filename).stem}.processed.json')
        with open(output_filename, 'w') as output_file:
            json.dump(extracted_data, output_file, indent=4)

    return "OK"


@s1.get("/aircraft/")
def list_aircraft(num_results: int = 100, page: int = 0) -> list[dict]:
    """List all the available aircraft, its registration and type ordered by
    icao asc
    """
    # TODO
    prepared_dir = Path(settings.prepared_dir) / "day=20231101"

    if not prepared_dir.exists():
        raise HTTPException(status_code=404, detail="Prepared data not found")

    aircraft_set = set()
    aircraft_list = []

    # Read the prepared JSON files and collect aircraft data
    for json_file in prepared_dir.glob("*.json"):
        try:
            with open(json_file, 'r') as file:
                data = json.load(file)
                for aircraft in data:
                    icao = aircraft["icao"]
                    if icao not in aircraft_set:
                        aircraft_set.add(icao)
                        aircraft_list.append({
                            "icao": icao,
                            "registration": aircraft["registration"],
                            "type": aircraft["type"]
                        })

        except json.decoder.JSONDecodeError as e:
            print(f"Error reading file {json_file}: {e}")
            continue  # Skip this file and continue with the next
    # Sort the list of aircraft by the 'icao' code in ascending order
    aircraft_list.sort(key=lambda x: x['icao'])

    # # Implement pagination
    # start = page * num_results
    # end = start + num_results
    # paginated_aircraft = aircraft_list[start:end]

    return aircraft_list


@s1.get("/aircraft/{icao}/positions")
def get_aircraft_position(icao: str, num_results: int = 1000, page: int = 0) -> list[dict]:
    """Returns all the known positions of an aircraft ordered by time (asc)
    If an aircraft is not found, return an empty list.
    """
    # TODO
    prepared_dir = Path(settings.prepared_dir) / "day=20231101"

    if not prepared_dir.exists():
        print("Prepared directory not found")
        raise HTTPException(status_code=404, detail="Prepared data not found")

    positions = []

    for json_file in prepared_dir.glob("*.processed.json"):
        try:
            with open(json_file, 'r') as file:
                data = json.load(file)
                for record in data:
                    if record["icao"] == icao:
                        positions.append({
                            "timestamp": record["timestamp"],
                            "lat": record["latitude"],
                            "lon": record["longitude"]
                        })
        except json.decoder.JSONDecodeError as e:
            print(f"Error reading file {json_file}: {e}")
            continue

    # Sort positions by timestamp
    positions.sort(key=lambda x: x['timestamp'])

    # Implement pagination
    start = page * num_results
    end = start + num_results
    paginated_positions = positions[start:end]
    print(f"Returning positions: {paginated_positions}")

    return paginated_positions


@s1.get("/aircraft/{icao}/stats")
def get_aircraft_statistics(icao: str) -> dict:
    """Returns different statistics about the aircraft

    * max_altitude_baro
    * max_ground_speed
    * had_emergency
    """
    # TODO
    prepared_dir = Path(settings.prepared_dir) / "day=20231101"
    if not prepared_dir.exists():
        raise HTTPException(status_code=404, detail="Prepared data not found")

    max_altitude_baro = 0
    max_ground_speed = 0
    had_emergency = False

    for json_file in prepared_dir.glob("*.processed.json"):
        with open(json_file, 'r') as file:
            data = json.load(file)
            for record in data:
                if record["icao"] == icao:
                    # Check and convert altitude_baro if it's numeric
                    altitude_baro = record.get("altitude_baro", "0")
                    # Check if altitude_baro is a digit and convert it to an integer
                    if isinstance(altitude_baro, str) and altitude_baro.isdigit():
                        altitude_baro = int(altitude_baro)
                    else:
                        altitude_baro = 0

                    max_altitude_baro = max(max_altitude_baro, altitude_baro)

                    # Convert ground_speed to float and handle non-numeric values
                    ground_speed = record.get("ground_speed", "0")
                    try:
                        ground_speed = float(ground_speed)
                    except ValueError:
                        ground_speed = 0.0

                    max_ground_speed = max(max_ground_speed, ground_speed)

                    # Check for emergency
                    if record.get("emergency", "") not in ["", "none"]:
                        had_emergency = True

    return {
        "max_altitude_baro": max_altitude_baro,
        "max_ground_speed": max_ground_speed,
        "had_emergency": had_emergency
    }


# def clean_data_directories():
#     raw_dir = Path(settings.raw_dir) / "day=20231101"
#     prepared_dir = Path(settings.prepared_dir) / "day=20231101"
#
#     # Delete files in the raw data directory
#     if raw_dir.exists() and raw_dir.is_dir():
#         shutil.rmtree(raw_dir)
#         print(f"Deleted all files in {raw_dir}")
#
#     # Delete files in the prepared data directory
#     if prepared_dir.exists() and prepared_dir.is_dir():
#         shutil.rmtree(prepared_dir)
#         print(f"Deleted all files in {prepared_dir}")
#
#     # Recreate the empty directories
#     raw_dir.mkdir(parents=True, exist_ok=True)
#     prepared_dir.mkdir(parents=True, exist_ok=True)
#     print("Recreated empty directories")