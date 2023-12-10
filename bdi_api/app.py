import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from starlette import status
from starlette.responses import JSONResponse

import bdi_api
from bdi_api.examples import v0_router
#from bdi_api.s1.solution import s1
from bdi_api.s1.exercise import s1

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator:
    logger.info("Application started. You can check the documentation in https://localhost:8000/docs/")
    yield
    # Shut Down
    logger.warning("Application shutdown")


app = FastAPI()
app.include_router(v0_router)
app.include_router(s1)


@app.get("/health", status_code=200)
async def get_health() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content="ok",
    )


@app.get("/version", status_code=200)
async def get_version() -> dict:
    return {"version": bdi_api.__version__}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000, access_log=False)
