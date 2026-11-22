import httpx

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from .orchestrator import OrchestratorError
from .schemas import MessageRequest, MessageResponse


router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ermes-backend",
    }


@router.get("/ready")
async def ready(request: Request):
    orchestrator = request.app.state.orchestrator

    try:
        await orchestrator.health()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Orchestrator is unavailable: {exc}",
        ) from exc

    return {
        "status": "ok",
        "orchestrator": "available",
    }


@router.post(
    "/v1/messages",
    response_model=MessageResponse,
)
async def send_message(
    payload: MessageRequest,
    request: Request,
):
    orchestrator = request.app.state.orchestrator

    try:
        result = await orchestrator.send_message(
            payload.message
        )

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Orchestrator returned an HTTP error: "
                f"{exc.response.status_code}"
            ),
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Cannot contact orchestrator: {exc}",
        ) from exc

    return MessageResponse(
        status=result["status"],
        response=result["response"],
    )


@router.post("/v1/messages/stream")
async def stream_message(
    payload: MessageRequest,
    request: Request,
):
    orchestrator = request.app.state.orchestrator

    try:
        upstream = await orchestrator.stream_message(
            payload.message
        )

    except OrchestratorError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Cannot contact orchestrator: {exc}",
        ) from exc

    async def relay_stream():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()

    return StreamingResponse(
        relay_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
