import logging
import os
from pathlib import Path
from uuid import UUID, uuid4

from anyio import Path as AsyncPath
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

MAX_FILE_BYTES = 25 * 1024 * 1024
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/filestorage", tags=["file storage"])


class StoredFile(BaseModel):
    id: UUID
    name: str
    size: int


@router.post("/files", status_code=201, response_model=StoredFile)
async def upload_file(
    request: Request,
    filename: str = Query(min_length=1, max_length=200),
) -> StoredFile:
    """Store one file sent as the request body."""
    if (
        filename in {".", ".."}
        or not filename.strip()
        or any(character in "/\\" or ord(character) < 32 for character in filename)
        or len(filename.encode("utf-8")) > 200
    ):
        raise HTTPException(422, "Invalid filename")

    data_root = os.getenv("ERMES_DATA_ROOT")
    if not data_root:
        raise HTTPException(503, "File storage is unavailable")

    file_id = uuid4()
    storage = AsyncPath(Path(data_root) / "backend" / "filestorage")
    temporary = storage / f".{file_id}.upload"
    destination = storage / f"{file_id}--{filename}"
    size = 0

    try:
        await storage.mkdir(parents=True, exist_ok=True)
        try:
            async with await temporary.open("xb") as file:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > MAX_FILE_BYTES:
                        raise HTTPException(413, "Files must be 25 MiB or smaller")
                    await file.write(chunk)
            await temporary.rename(destination)
        finally:
            await temporary.unlink(missing_ok=True)
    except OSError as exc:
        logger.exception("Could not store uploaded file")
        raise HTTPException(503, "File storage is unavailable") from exc

    return StoredFile(id=file_id, name=filename, size=size)
