from fastapi import APIRouter, HTTPException, Request


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
