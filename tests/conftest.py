"""Shared pytest fixtures.

Uses an in-memory SQLite database for fast, isolated tests. Each test gets a
fresh schema created from ``Base.metadata``.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_BOOTSTRAP"] = "0"

from app.core.database import Base, get_db
from app.main import app
from app import models  # noqa: F401 - register models with Base


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # SQLite doesn't support Postgres UUID columns natively; SQLAlchemy maps
    # them to CHAR(32) automatically when the dialect lacks native support.
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # Now safe to use as context manager: DB bootstrap is disabled for tests.
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
