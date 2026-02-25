import logging
from json import JSONDecodeError

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import services
from app.auth import create_access_token
from app.db import get_db
from app.schemas import SignInRequest, TokenResponse, UserCreate, UserDetail


router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/signup", response_model=UserDetail, status_code=201)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    try:
        created = services.create_user(db, user)
        logger.info("User signup success user_id=%s", created.user_id)
        return created
    except ValueError as exc:
        logger.warning("User signup validation failed user_id=%s error=%s", user.user_id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error during signup user_id=%s", user.user_id)
        raise HTTPException(
            status_code=500,
            detail="Database error during signup. Recheck database schema.",
        ) from exc


@router.post(
    "/signin",
    response_model=TokenResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": SignInRequest.model_json_schema(),
                    "example": {
                        "email": "customer@example.com",
                        "password": "Str0ngPassw0rd!",
                    },
                }
            },
        }
    },
)
async def signin(
    request: Request,
    db: Session = Depends(get_db),
):
    email = ""
    password = ""

    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        try:
            payload = SignInRequest.model_validate(await request.json())
            email = payload.email
            password = payload.password
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        except JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="Malformed JSON body") from exc
    else:
        # Swagger OAuth2 Authorize sends x-www-form-urlencoded with username/password.
        form = await request.form()
        email = str(form.get("username", ""))
        password = str(form.get("password", ""))

    if not email or not password:
        raise HTTPException(status_code=422, detail="Email/username and password are required")

    try:
        user = services.authenticate_user(db, email, password)
        if not user:
            logger.warning("Signin failed for email=%s", email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        logger.info("Signin success user_id=%s", user.user_id)
        return TokenResponse(access_token=create_access_token(subject=str(user.user_id)))
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error during signin email=%s", email)
        raise HTTPException(
            status_code=500,
            detail="Database error during signin. Recheck database schema.",
        ) from exc
