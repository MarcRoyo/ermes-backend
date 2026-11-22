import os

from dataclasses import dataclass


def _build_websocket_url(
    http_url: str,
) -> str:
    http_url = http_url.rstrip("/")

    if http_url.startswith(
        "https://"
    ):
        base_url = (
            "wss://"
            + http_url[len("https://"):]
        )

    elif http_url.startswith(
        "http://"
    ):
        base_url = (
            "ws://"
            + http_url[len("http://"):]
        )

    else:
        raise ValueError(
            "ERMES_ORCHESTRATOR_URL must start "
            "with http:// or https://"
        )

    return (
        f"{base_url}/v1/ws"
    )


@dataclass(
    frozen=True
)
class Settings:
    orchestrator_url: str
    orchestrator_ws_url: str

    allowed_origins: tuple[
        str,
        ...
    ]

    @classmethod
    def from_env(
        cls,
    ) -> "Settings":

        orchestrator_url = (
            os.environ.get(
                "ERMES_ORCHESTRATOR_URL",
                "http://localhost:8090",
            )
            .rstrip("/")
        )

        orchestrator_ws_url = (
            os.environ.get(
                "ERMES_ORCHESTRATOR_WS_URL"
            )
            or _build_websocket_url(
                orchestrator_url
            )
        )

        origins_raw = os.environ.get(
            "ERMES_ALLOWED_ORIGINS",
            "http://localhost:5173",
        )

        allowed_origins = tuple(
            origin.strip()
            for origin
            in origins_raw.split(",")
            if origin.strip()
        )

        return cls(
            orchestrator_url=(
                orchestrator_url
            ),
            orchestrator_ws_url=(
                orchestrator_ws_url
            ),
            allowed_origins=(
                allowed_origins
            ),
        )