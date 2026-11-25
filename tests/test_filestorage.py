import asyncio
from uuid import UUID

import httpx

from ermes_backend import filestorage
from ermes_backend.main import app


def test_upload_persists_bytes_and_rejects_invalid_files(tmp_path, monkeypatch):
    monkeypatch.setenv("ERMES_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(filestorage, "MAX_FILE_BYTES", 10)
    storage = tmp_path / "backend" / "filestorage"

    async def upload_files():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://backend"
        ) as client:
            response = await client.post(
                "/v1/filestorage/files",
                params={"filename": "comptes.csv"},
                content=b"debit,100",
            )
            assert response.status_code == 201
            metadata = response.json()
            file_id = UUID(metadata["id"])
            assert metadata["name"] == "comptes.csv"
            assert metadata["size"] == 9
            stored = storage / f"{file_id}--comptes.csv"
            assert stored.read_bytes() == b"debit,100"

            for name, data, status in [
                ("../other.txt", b"content", 422),
                ("large.txt", b"x" * 11, 413),
            ]:
                response = await client.post(
                    "/v1/filestorage/files", params={"filename": name}, content=data
                )
                assert response.status_code == status
                assert list(storage.iterdir()) == [stored]

    asyncio.run(upload_files())
