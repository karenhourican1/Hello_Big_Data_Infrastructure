from fastapi import APIRouter, status

s3 = APIRouter(
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Something is wrong with the request"},
    },
    prefix="/api/s1",
    tags=["s1"],
)


@s3.post("/aircraft/prepare")
def prepare_data() -> str:
    """Downloads the data and prepares it in the way you think it's better
    for the analysis.

    data: https://samples.adsbexchange.com/readsb-hist/2023/11/01/
    documentation: https://www.adsbexchange.com/version-2-api-wip/
        See "Trace File Fields" section

    Think about the way you organize the information inside the folder
    and the level of preprocessing you might need.

    To manipulate the data use any library you feel comfortable with.
    Just make sure to configure it in the `pyproject.toml` file
    so it can be installed using `poetry update`.
    """
    # TODO Same as S1 exercise but now using S3 bucket and Aurora
    return "OK"


@s3.get("/aircraft/")
def list_aircraft() -> list[dict]:
    """List all the available aircraft, its registration and type ordered by
    icao asc
    """
    # TODO Same as S1 exercise but now using S3 bucket and Aurora
    return [{"icao": "0d8300", "registration": "YV3382", "type": "LJ31"}]


@s3.get("/aircraft/{icao}/positions")
def get_aircraft_position(icao: str) -> list[dict]:
    """Returns all the known positions of an aircraft ordered by time (asc)
    If an aircraft is not found, return an empty list.
    """
    # TODO Same as S1 exercise but now using S3 bucket and Aurora
    return [{"timestamp": 1609275898.6, "lat": 30.404617, "lon": -86.476566}]


@s3.get("/aircraft/{icao}/stats")
def get_aircraft_statistics(icao: str) -> dict:
    """Returns different statistics about the aircraft

    * max_altitude
    * max_ground_speed
    * had_emergency
    """
    # TODO Same as S1 exercise but now using S3 bucket and Aurora
    return {"max_altitude": 300000, "max_ground_speed": 493, "had_emergency": False}
