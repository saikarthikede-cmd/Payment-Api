import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app import services
from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import UserDetail

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)


@router.get("/{user_id}", response_model=UserDetail)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user details by user ID."""
    if user_id != current_user.user_id:
        logger.warning(
            "Forbidden user fetch requester=%s target=%s",
            current_user.user_id,
            user_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    user = services.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("", response_model=List[UserDetail])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all users."""
    users = (
        db.query(User)
        .filter(User.user_id == current_user.user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    logger.info("Listed users requester=%s returned=%s", current_user.user_id, len(users))
    return users
