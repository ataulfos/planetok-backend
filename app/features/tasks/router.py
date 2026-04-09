"""Tasks router — stub. The ``feat/tasks`` subagent implements the endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/_ping")
def ping() -> dict:
    return {"feature": "tasks", "status": "stub"}
