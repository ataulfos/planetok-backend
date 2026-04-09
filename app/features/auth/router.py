from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.auth.models import User

router = APIRouter()


class AuthRequest(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=255)


class UserResponse(BaseModel):
    id: str
    username: str
    created_at: str

    @classmethod
    def from_orm_user(cls, user: User) -> "UserResponse":
        created_at = user.created_at
        if isinstance(created_at, datetime):
            created_at_str = created_at.replace(tzinfo=None).isoformat() + "Z"
        else:
            created_at_str = str(created_at)
        return cls(id=str(user.id), username=user.username, created_at=created_at_str)


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register(payload: AuthRequest, db: Session = Depends(get_db)) -> UserResponse:
    user = User(username=payload.username, password=payload.password)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="username already exists"
        )
    db.refresh(user)
    return UserResponse.from_orm_user(user)


@router.post("/login", response_model=UserResponse)
def login(payload: AuthRequest, db: Session = Depends(get_db)) -> UserResponse:
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or user.password != payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials"
        )
    return UserResponse.from_orm_user(user)
