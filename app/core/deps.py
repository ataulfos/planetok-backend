from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db


def get_current_user(
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: Session = Depends(get_db),
):
    """Simulated auth: trusts the X-User-Id header.

    Security hardening (hashing, JWT, etc.) is marked as a future improvement
    in the README per the agreed scope for this technical test.
    """
    # Local import prevents circular imports at module load time.
    from app.features.auth.models import User

    try:
        user_uuid = UUID(x_user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid X-User-Id header",
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user not found",
        )
    return user
