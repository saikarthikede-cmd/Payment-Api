from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse, UserDetail
from app import services

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user."""
    try:
        new_user = services.create_user(db, user)
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}", response_model=UserDetail)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user details by user ID."""
    if user_id != current_user.user_id:
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
    return [user for user in users if user.user_id == current_user.user_id]
