from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app import services
from app.auth import create_access_token, get_current_user
from app.db import get_db
from app.models import User
from app.schemas import SignInRequest, TokenResponse, UserCreate, UserDetail


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserDetail, status_code=201)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    try:
        return services.create_user(db, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database error during signup. Recheck database schema.",
        ) from exc


@router.post("/signin", response_model=TokenResponse)
def signin(credentials: SignInRequest, db: Session = Depends(get_db)):
    try:
        user = services.authenticate_user(db, credentials.email, credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        return TokenResponse(access_token=create_access_token(subject=user.user_id))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail="Database error during signin. Recheck database schema.",
        ) from exc


@router.get("/me", response_model=UserDetail)
def me(current_user: User = Depends(get_current_user)):
    return current_user
