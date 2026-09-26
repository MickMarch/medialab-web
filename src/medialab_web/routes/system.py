from fastapi import APIRouter

from medialab_web._version import version

router = APIRouter()


@router.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "online", "version": version}
