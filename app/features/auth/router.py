"""Auth router — stub. The ``feat/auth`` subagent implements the endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/_ping")
def ping() -> dict:
    return {"feature": "auth", "status": "stub"}
