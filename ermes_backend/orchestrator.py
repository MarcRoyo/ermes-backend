import httpx


class OrchestratorError(RuntimeError):
    pass


class OrchestratorClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(
                connect=5.0,
                read=None,
                write=30.0,
                pool=5.0,
            ),
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def health(self) -> dict:
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()

    async def send_message(self, message: str) -> dict:
        response = await self.client.post(
            "/v1/messages",
            json={"message": message},
        )
        response.raise_for_status()
        return response.json()

    async def stream_message(self, message: str) -> httpx.Response:
        request = self.client.build_request(
            "POST",
            "/v1/messages/stream",
            headers={
                "Accept": "text/event-stream",
                "Content-Type": "application/json",
            },
            json={"message": message},
        )

        response = await self.client.send(
            request,
            stream=True,
        )

        if not response.is_success:
            body = await response.aread()
            await response.aclose()

            raise OrchestratorError(
                "Orchestrator returned "
                f"{response.status_code}: "
                f"{body.decode(errors='replace')}"
            )

        return response
