import asyncio
import logging

from fastapi import (
    APIRouter,
    WebSocket,
)
from starlette.websockets import (
    WebSocketState,
)

from websockets.exceptions import (
    ConnectionClosed,
)

from .orchestrator_ws import (
    open_orchestrator_websocket,
)


async def _close_client(
    websocket: WebSocket,
    *,
    code: int = 1000,
) -> None:

    if (
        websocket.application_state
        == WebSocketState.CONNECTED
    ):
        try:
            await websocket.close(
                code=code
            )

        except RuntimeError:
            pass


async def _client_to_orchestrator(
    *,
    client: WebSocket,
    orchestrator,
) -> None:
    """
    Relay frames:

        frontend
            ↓
        backend
            ↓
        orchestrator
    """

    while True:

        message = await client.receive()

        message_type = message.get(
            "type"
        )

        if (
            message_type
            == "websocket.disconnect"
        ):
            return

        if (
            message_type
            != "websocket.receive"
        ):
            continue

        text = message.get(
            "text"
        )

        binary = message.get(
            "bytes"
        )

        if text is not None:

            await orchestrator.send(
                text
            )

            continue

        #
        # Ermes protocol V1 uses JSON text frames only.
        #
        if binary is not None:

            await _close_client(
                client,
                code=1003,
            )

            return


async def _orchestrator_to_client(
    *,
    orchestrator,
    client: WebSocket,
) -> None:
    """
    Relay frames:

        orchestrator
            ↓
        backend
            ↓
        frontend
    """

    try:

        async for message in orchestrator:

            if isinstance(
                message,
                str,
            ):
                await client.send_text(
                    message
                )

            else:
                #
                # Protocol V1 doesn't use
                # binary frames.
                #
                await _close_client(
                    client,
                    code=1003,
                )

                return

    except ConnectionClosed:
        return


async def _relay(
    *,
    client: WebSocket,
    orchestrator,
) -> None:
    """
    Run both relay directions concurrently.

    If either side disconnects, cancel the
    opposite relay task.
    """

    client_to_orchestrator = (
        asyncio.create_task(
            _client_to_orchestrator(
                client=client,
                orchestrator=(
                    orchestrator
                ),
            ),
            name=(
                "ws-client-to-orchestrator"
            ),
        )
    )

    orchestrator_to_client = (
        asyncio.create_task(
            _orchestrator_to_client(
                orchestrator=(
                    orchestrator
                ),
                client=client,
            ),
            name=(
                "ws-orchestrator-to-client"
            ),
        )
    )

    tasks = {
        client_to_orchestrator,
        orchestrator_to_client,
    }

    _, pending = await asyncio.wait(
        tasks,
        return_when=(
            asyncio.FIRST_COMPLETED
        ),
    )

    for task in pending:
        task.cancel()

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    for result in results:

        if isinstance(
            result,
            asyncio.CancelledError,
        ):
            continue

        if isinstance(
            result,
            BaseException,
        ):
            raise result


def create_realtime_router(
    *,
    orchestrator_ws_url: str,
    logger: logging.Logger,
) -> APIRouter:

    router = APIRouter()

    @router.websocket(
        "/v1/ws"
    )
    async def websocket_gateway(
        websocket: WebSocket,
    ) -> None:

        await websocket.accept()

        logger.info(
            "Public WebSocket connected"
        )

        try:

            async with (
                open_orchestrator_websocket(
                    url=(
                        orchestrator_ws_url
                    ),
                    logger=logger,
                )
            ) as orchestrator:

                await _relay(
                    client=websocket,
                    orchestrator=(
                        orchestrator
                    ),
                )

        except Exception:

            logger.exception(
                "WebSocket gateway failure"
            )

            await _close_client(
                websocket,
                code=1011,
            )

        finally:

            await _close_client(
                websocket
            )

            logger.info(
                "Public WebSocket disconnected"
            )

    return router