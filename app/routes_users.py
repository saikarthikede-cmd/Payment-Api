import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app import services
from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse, UserDetail

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)


@router.post("", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user."""
    try:
        new_user = services.create_user(db, user)
        logger.info("User created via /users user_id=%s", new_user.user_id)
        return new_user
    except ValueError as e:
        logger.warning("User creation via /users failed user_id=%s error=%s", user.user_id, e)
        raise HTTPException(status_code=400, detail=str(e))


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
    users = services.list_users(db, skip=skip, limit=limit)
    logger.info("Listed users requester=%s returned=%s", current_user.user_id, len(users))
    return [user for user in users if user.user_id == current_user.user_id] # type: ignore
