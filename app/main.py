from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app import models  # noqa: F401 - register SQLAlchemy models
from app.features.auth.router import router as auth_router
from app.features.tasks.router import router as tasks_router

app = FastAPI(title="TaskAI Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Simple bootstrap for tight-timeline demo; Alembic migrations are a
    # future improvement (see README).
    Base.metadata.create_all(bind=engine)


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
