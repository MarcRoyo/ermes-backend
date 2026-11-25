import httpx


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
