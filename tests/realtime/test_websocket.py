import json
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

import ermes_backend.realtime.websocket as websocket_module

from ermes_backend.realtime.websocket import (
    create_realtime_router,
)


class FakeOrchestratorWebSocket:
    """
    Fake internal WebSocket used by the backend tests.

    It behaves like the websocket connection that normally exists
    between:

        ermes-backend
            ↓
        ermes-orchestrator
    """

    def __init__(self):
        self.received_from_backend: list[str] = []

        self._messages: list[str] = []
        self._closed = False

    async def send(
        self,
        message: str,
    ) -> None:
        """
        Receive a frame sent by the backend towards the orchestrator.
        """

        self.received_from_backend.append(
            message
        )

        data = json.loads(
            message
        )

        #
        # Simulate the responses that the real orchestrator
        # would produce.
        #

        if data["type"] == "session.sync":

            self._messages.append(
                json.dumps(
                    {
                        "version": 1,
                        "type": "session.synced",
                        "id": "ctl_test",
                        "session_id": data[
                            "session_id"
                        ],
                        "timestamp": (
                            "2026-11-22T07:00:00Z"
                        ),
                        "correlation_id": data[
                            "id"
                        ],
                        "payload": {
                            "current_sequence": 0,
                        },
                    }
                )
            )

        elif data["type"] == "message.commit":

            self._messages.append(
                json.dumps(
                    {
                        "version": 1,
                        "type": "message.committed",
                        "id": "evt_1",
                        "session_id": data[
                            "session_id"
                        ],
                        "timestamp": (
                            "2026-11-22T07:00:01Z"
                        ),
                        "sequence": 1,
                        "correlation_id": data[
                            "id"
                        ],
                        "payload": {
                            "message_id": "msg_1",
                            "source": "keyboard",
                            "text": data[
                                "payload"
                            ]["text"],
                            "utterance_id": None,
                        },
                    }
                )
            )

    def __aiter__(
        self,
    ):
        return self

    async def __anext__(
        self,
    ):
        #
        # Wait until a fake orchestrator response becomes
        # available.
        #
        import asyncio

        while not self._messages:

            if self._closed:
                raise StopAsyncIteration

            await asyncio.sleep(
                0.001
            )

        return self._messages.pop(
            0
        )

    async def close(
        self,
    ):
        self._closed = True


def make_app(
    monkeypatch,
):
    app = FastAPI()

    fake_orchestrator = (
        FakeOrchestratorWebSocket()
    )

    @asynccontextmanager
    async def fake_open_orchestrator_websocket(
        *,
        url,
        logger,
    ):
        yield fake_orchestrator

        await fake_orchestrator.close()

    monkeypatch.setattr(
        websocket_module,
        "open_orchestrator_websocket",
        fake_open_orchestrator_websocket,
    )

    app.include_router(
        create_realtime_router(
            orchestrator_ws_url=(
                "ws://orchestrator:8090/v1/ws"
            ),
            logger=logging.getLogger(
                "test"
            ),
        )
    )

    return (
        app,
        fake_orchestrator,
    )


def session_sync():
    return {
        "version": 1,
        "type": "session.sync",
        "id": "cmd_sync_1",
        "session_id": "ses_test_1",
        "timestamp": (
            "2026-11-22T07:00:00Z"
        ),
        "payload": {
            "last_sequence": None,
        },
    }


def message_commit():
    return {
        "version": 1,
        "type": "message.commit",
        "id": "cmd_1",
        "session_id": "ses_test_1",
        "timestamp": (
            "2026-11-22T07:00:01Z"
        ),
        "payload": {
            "draft_id": None,
            "revision": None,
            "source": "keyboard",
            "text": "Hello Ermes",
        },
    }


def test_session_sync_is_relayed_to_orchestrator(
    monkeypatch,
):
    app, orchestrator = make_app(
        monkeypatch
    )

    with TestClient(app) as client:

        with client.websocket_connect(
            "/v1/ws"
        ) as ws:

            command = session_sync()

            ws.send_json(
                command
            )

            response = (
                ws.receive_json()
            )

            assert (
                response["type"]
                == "session.synced"
            )

            assert (
                response["session_id"]
                == "ses_test_1"
            )

            assert (
                response["correlation_id"]
                == "cmd_sync_1"
            )

            assert (
                response["payload"][
                    "current_sequence"
                ]
                == 0
            )

            #
            # Verify that the backend didn't modify
            # the command.
            #
            assert len(
                orchestrator.received_from_backend
            ) == 1

            forwarded = json.loads(
                orchestrator
                .received_from_backend[0]
            )

            assert (
                forwarded
                == command
            )


def test_message_commit_is_relayed_bidirectionally(
    monkeypatch,
):
    app, orchestrator = make_app(
        monkeypatch
    )

    with TestClient(app) as client:

        with client.websocket_connect(
            "/v1/ws"
        ) as ws:

            #
            # First synchronize the session.
            #

            ws.send_json(
                session_sync()
            )

            synced = (
                ws.receive_json()
            )

            assert (
                synced["type"]
                == "session.synced"
            )

            #
            # Now send the user message.
            #

            command = message_commit()

            ws.send_json(
                command
            )

            event = (
                ws.receive_json()
            )

            assert (
                event["type"]
                == "message.committed"
            )

            assert (
                event["sequence"]
                == 1
            )

            assert (
                event["correlation_id"]
                == "cmd_1"
            )

            assert (
                event["payload"][
                    "message_id"
                ]
                == "msg_1"
            )

            assert (
                event["payload"]["text"]
                == "Hello Ermes"
            )

            #
            # The backend must have forwarded both
            # messages without interpreting them.
            #

            assert len(
                orchestrator.received_from_backend
            ) == 2

            forwarded_commit = json.loads(
                orchestrator
                .received_from_backend[1]
            )

            assert (
                forwarded_commit
                == command
            )


def test_backend_does_not_modify_protocol_frames(
    monkeypatch,
):
    app, orchestrator = make_app(
        monkeypatch
    )

    with TestClient(app) as client:

        with client.websocket_connect(
            "/v1/ws"
        ) as ws:

            original = {
                "version": 1,
                "type": "session.sync",
                "id": "cmd_original",
                "session_id": "ses_original",
                "timestamp": (
                    "2026-11-22T07:15:00Z"
                ),
                "payload": {
                    "last_sequence": 42,
                },
            }

            ws.send_text(
                json.dumps(
                    original
                )
            )

            #
            # Consume fake orchestrator response.
            #
            ws.receive_json()

            forwarded = json.loads(
                orchestrator
                .received_from_backend[0]
            )

            assert (
                forwarded
                == original
            )


def test_multiple_commands_use_same_internal_connection(
    monkeypatch,
):
    app, orchestrator = make_app(
        monkeypatch
    )

    with TestClient(app) as client:

        with client.websocket_connect(
            "/v1/ws"
        ) as ws:

            ws.send_json(
                session_sync()
            )

            ws.receive_json()

            ws.send_json(
                message_commit()
            )

            ws.receive_json()

            assert len(
                orchestrator.received_from_backend
            ) == 2

            first = json.loads(
                orchestrator
                .received_from_backend[0]
            )

            second = json.loads(
                orchestrator
                .received_from_backend[1]
            )

            assert (
                first["type"]
                == "session.sync"
            )

            assert (
                second["type"]
                == "message.commit"
            )


def test_gateway_endpoint_exists(
    monkeypatch,
):
    app, _ = make_app(
        monkeypatch
    )

    with TestClient(app) as client:

        with client.websocket_connect(
            "/v1/ws"
        ) as ws:

            ws.send_json(
                session_sync()
            )

            response = (
                ws.receive_json()
            )

            assert (
                response["type"]
                == "session.synced"
            )