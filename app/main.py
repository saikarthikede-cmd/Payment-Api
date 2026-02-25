import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import init_db
from app.logging_config import setup_logging
from app.routes_auth import router as auth_router
from app.routes_orders import router as orders_router
from app.routes_users import router as users_router
from app.routes_wallet import router as wallet_router

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Application startup initiated")
    if settings.app_env.lower() in {"production", "prod"} and len(settings.jwt_secret_key) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters in production")
    init_db()
    logger.info("Application startup completed")
    yield
    logger.info("Application shutdown completed")


app = FastAPI(title="Payment API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(orders_router)
app.include_router(wallet_router)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
    except Exception:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.exception(
            "request method=%s path=%s status=500 duration_ms=%s",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
def root():
    return {"message": "Payment API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}
