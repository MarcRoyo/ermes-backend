import logging
import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .config import Settings
from .orchestrator import OrchestratorClient
from .realtime.websocket import (
    create_realtime_router,
)


#
# Logging
#

logger = logging.getLogger(
    "ermes-backend"
)

handler = logging.StreamHandler(
    sys.stdout
)

handler.setFormatter(
    logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s"
    )
)

logger.addHandler(
    handler
)

logger.setLevel(
    logging.INFO
)

logger.propagate = False


#
# Configuration
#

settings = Settings.from_env()


#
# Application lifecycle
#

@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    logger.info(
        "Starting Ermes backend"
    )

    orchestrator = OrchestratorClient(
        settings.orchestrator_url
    )

    app.state.orchestrator = (
        orchestrator
    )

    try:
        yield

    finally:
        logger.info(
            "Stopping Ermes backend"
        )

        await orchestrator.close()


#
# FastAPI application
#

app = FastAPI(
    title="Ermes Backend",
    version="0.1.0",
    lifespan=lifespan,
)


#
# CORS
#

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(
        settings.allowed_origins
    ),
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "OPTIONS",
    ],
    allow_headers=[
        "Accept",
        "Content-Type",
        "Authorization",
    ],
)


#
# HTTP API
#

app.include_router(
    router
)


#
# Realtime WebSocket gateway
#

app.include_router(
    create_realtime_router(
        orchestrator_ws_url=(
            settings.orchestrator_ws_url
        ),
        logger=logger,
    )
)