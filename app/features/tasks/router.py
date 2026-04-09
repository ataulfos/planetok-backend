from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.features.ai.agent import AIAgentError, analyze_task
from app.features.auth.models import User
from app.features.tasks.models import Subtask, Task

router = APIRouter()

TaskStatus = Literal["pending", "completed"]
TaskCategory = Literal["personal", "work", "urgent"]


def _iso(dt: datetime) -> str:
    return dt.replace(tzinfo=None).isoformat() + "Z"


class SubtaskResponse(BaseModel):
    id: str
    title: str
    order: int
    completed: bool

    @classmethod
    def from_orm_obj(cls, s: Subtask) -> "SubtaskResponse":
        return cls(id=str(s.id), title=s.title, order=s.order, completed=s.completed)


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus
    category: Optional[TaskCategory] = None
    created_at: str
    updated_at: str
    subtasks: list[SubtaskResponse]

    @classmethod
    def from_orm_obj(cls, t: Task) -> "TaskResponse":
        return cls(
            id=str(t.id),
            title=t.title,
            description=t.description or "",
            status=t.status,  # type: ignore[assignment]
            category=t.category,  # type: ignore[assignment]
            created_at=_iso(t.created_at),
            updated_at=_iso(t.updated_at),
            subtasks=[SubtaskResponse.from_orm_obj(s) for s in (t.subtasks or [])],
        )


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=10000)
    status: Optional[TaskStatus] = None
    category: Optional[TaskCategory] = None


class SubtaskUpdateRequest(BaseModel):
    completed: bool


def _get_task_or_404(db: Session, task_id: UUID, owner_id: UUID) -> Task:
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .filter(Task.owner_id == owner_id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.get("/", response_model=list[TaskResponse])
def list_tasks(
    status_filter: Optional[TaskStatus] = Query(default=None, alias="status"),
    ordering: str = Query(default="-created_at"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TaskResponse]:
    q = db.query(Task).filter(Task.owner_id == user.id)
    if status_filter is not None:
        q = q.filter(Task.status == status_filter)

    ordering_map = {
        "created_at": Task.created_at.asc(),
        "-created_at": Task.created_at.desc(),
        "updated_at": Task.updated_at.asc(),
        "-updated_at": Task.updated_at.desc(),
    }
    order_clause = ordering_map.get(ordering)
    if order_clause is None:
        raise HTTPException(status_code=422, detail="invalid ordering")
    q = q.order_by(order_clause)

    tasks = q.all()
    return [TaskResponse.from_orm_obj(t) for t in tasks]


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=TaskResponse)
def create_task(
    payload: TaskCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    task = Task(
        owner_id=user.id,
        title=payload.title,
        description=payload.description or "",
        status="pending",
        category=None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return TaskResponse.from_orm_obj(task)


@router.get("/{id}/", response_model=TaskResponse)
def get_task(
    id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    task = _get_task_or_404(db, id, user.id)
    return TaskResponse.from_orm_obj(task)


@router.patch("/{id}/", response_model=TaskResponse)
def update_task(
    id: UUID,
    payload: TaskUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    task = _get_task_or_404(db, id, user.id)

    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.status is not None:
        task.status = payload.status
    if payload.category is not None:
        task.category = payload.category

    db.commit()
    db.refresh(task)
    return TaskResponse.from_orm_obj(task)


@router.delete("/{id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    task = _get_task_or_404(db, id, user.id)
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{id}/analyze/", response_model=TaskResponse)
def analyze_task_endpoint(
    id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    task = _get_task_or_404(db, id, user.id)

    try:
        result = analyze_task(task.title, task.description or "")
    except AIAgentError as e:
        msg = str(e).lower()
        if "timeout" in msg:
            raise HTTPException(status_code=504, detail="ai agent timeout")
        raise HTTPException(status_code=502, detail="ai agent unavailable")

    category = result.get("category")
    subtasks = result.get("subtasks") or []
    if category not in ("personal", "work", "urgent"):
        raise HTTPException(status_code=502, detail="ai agent unavailable")
    if not isinstance(subtasks, list) or not all(isinstance(x, str) for x in subtasks):
        raise HTTPException(status_code=502, detail="ai agent unavailable")

    task.category = category

    # Replace existing subtasks.
    for existing in list(task.subtasks or []):
        db.delete(existing)
    db.flush()

    titles = [t.strip() for t in subtasks if t and t.strip()]
    titles = titles[:6] if len(titles) > 6 else titles
    if len(titles) < 2:
        # Guarantee at least 2 actionable steps.
        titles = titles + ["Review and refine details", "Schedule time to execute"]
        titles = titles[:2]

    for idx, title in enumerate(titles):
        db.add(Subtask(task_id=task.id, title=title, order=idx, completed=False))

    db.commit()
    db.refresh(task)
    return TaskResponse.from_orm_obj(task)


@router.patch("/{task_id}/subtasks/{subtask_id}/", response_model=SubtaskResponse)
def update_subtask(
    task_id: UUID,
    subtask_id: UUID,
    payload: SubtaskUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubtaskResponse:
    task = _get_task_or_404(db, task_id, user.id)
    subtask = (
        db.query(Subtask)
        .filter(Subtask.id == subtask_id)
        .filter(Subtask.task_id == task.id)
        .first()
    )
    if subtask is None:
        raise HTTPException(status_code=404, detail="subtask not found")
    subtask.completed = payload.completed
    db.commit()
    db.refresh(subtask)
    return SubtaskResponse.from_orm_obj(subtask)
