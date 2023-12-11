from fastapi import APIRouter, status, HTTPException

from bdi_api.settigns import Settings

import requests
import os
from pathlib import Path

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
    download_dir = Path(settings.raw_dir) / "day=20231101"
    download_dir.mkdir(parents=True, exist_ok=True)  # Ensures that the directory exists
    # BASE_URL
    for i in range(1000):
        # Adjusting the number to match the timestamp format in the file names
        # The timestamp increases by 5 seconds for each file
        timestamp = i * 5
        file_url = f"{BASE_URL}2023-11-01-{timestamp:06}Z.json"  # Include the date in the file name
        file_path = download_dir / f"2023-11-01-{timestamp:06}Z.json"

        if not file_path.exists():  # Check if the file has already been downloaded
            try:
                response = requests.get(file_url)
                response.raise_for_status()  # Will raise HTTPError if HTTP request returned an unsuccessful status code
                with open(file_path, 'wb') as f:
                    f.write(response.content)
            except requests.exceptions.HTTPError as http_err:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(http_err))
            except Exception as err:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))

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
    return "OK"


@s1.get("/aircraft/")
def list_aircraft(num_results: int = 100, page: int = 0) -> list[dict]:
    """List all the available aircraft, its registration and type ordered by
    icao asc
    """
    # TODO
    return [{"icao": "0d8300", "registration": "YV3382", "type": "LJ31"}]


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
