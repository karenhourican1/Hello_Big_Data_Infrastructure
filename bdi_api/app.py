import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from bdi_api.examples import v0_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator:
    logger.info("Application started. You can check the documentation in https://localhost:8000/docs/")
    yield
    # Shut Down
    logger.warning("Application shutdown")


app = FastAPI()
app.include_router(v0_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000, access_log=False)
