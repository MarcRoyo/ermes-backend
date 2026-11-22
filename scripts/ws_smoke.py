import asyncio
import json

from datetime import datetime, timezone

import websockets


URL = "ws://localhost:8091/v1/ws"
SESSION_ID = "ses_test_1"


def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


async def main():
    async with websockets.connect(
        URL
    ) as ws:

        print(
            f"Connected to {URL}"
        )

        #
        # 1. Synchronize session
        #
        sync = {
            "version": 1,
            "type": "session.sync",
            "id": "cmd_sync_1",
            "session_id": SESSION_ID,
            "timestamp": now(),
            "payload": {
                "last_sequence": None,
            },
        }

        print(
            "\n>>> session.sync"
        )

        await ws.send(
            json.dumps(sync)
        )

        response = json.loads(
            await ws.recv()
        )

        print(
            json.dumps(
                response,
                indent=2,
                ensure_ascii=False,
            )
        )

        #
        # 2. Commit a message
        #
        command = {
            "version": 1,
            "type": "message.commit",
            "id": "cmd_test_1",
            "session_id": SESSION_ID,
            "timestamp": now(),
            "payload": {
                "draft_id": None,
                "revision": None,
                "source": "keyboard",
                "text": (
                    "Explain briefly what "
                    "a neural network is"
                ),
            },
        }

        print(
            "\n>>> message.commit"
        )

        await ws.send(
            json.dumps(command)
        )

        #
        # 3. Print events until generation finishes
        #
        while True:

            raw = await ws.recv()

            event = json.loads(
                raw
            )

            print(
                "\n<<<",
                event.get("type"),
                "sequence=",
                event.get("sequence"),
            )

            print(
                json.dumps(
                    event,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            if event.get("type") in {
                "generation.completed",
                "generation.failed",
                "generation.cancelled",
            }:
                break


asyncio.run(
    main()
)