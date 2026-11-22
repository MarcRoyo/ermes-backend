import logging

from collections.abc import (
    AsyncIterator,
)
from contextlib import (
    asynccontextmanager,
)

from websockets.asyncio.client import (
    ClientConnection,
    connect,
)


@asynccontextmanager
async def open_orchestrator_websocket(
    *,
    url: str,
    logger: logging.Logger,
) -> AsyncIterator[
    ClientConnection
]:
    """
    Open the internal WebSocket connection from
    ermes-backend to ermes-orchestrator.
    """

    logger.info(
        "Connecting to orchestrator WebSocket "
        "url=%s",
        url,
    )

    async with connect(
        url,

        #
        # This is an internal Docker/network connection.
        # Do not route it through HTTP_PROXY / HTTPS_PROXY.
        #
        proxy=None,

        open_timeout=5,
        close_timeout=5,

        #
        # Native WebSocket heartbeat.
        #
        ping_interval=20,
        ping_timeout=20,

        #
        # Defensive upper bound for a protocol message.
        #
        max_size=2 * 1024 * 1024,
    ) as websocket:

        logger.info(
            "Connected to orchestrator "
            "WebSocket"
        )

        try:
            yield websocket

        finally:
            logger.info(
                "Orchestrator WebSocket "
                "connection closed"
            )