from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from app.models import Base

# Database engine with connection pooling and health checks
# pool_pre_ping ensures stale connections are recycled
# Default isolation level: READ COMMITTED (PostgreSQL default)
# This provides optimal balance between consistency and performance
# MVCC handles concurrent transactions without explicit locking
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    pool_pre_ping=not settings.database_url.startswith("sqlite"),
    connect_args=connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    _ensure_auth_schema_compatibility()


def _ensure_auth_schema_compatibility() -> None:
    """Backfill auth columns for older deployments without migrations."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    dialect = engine.dialect.name

    with engine.begin() as connection:
        if "password_hash" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
            connection.execute(text("UPDATE users SET password_hash = '' WHERE password_hash IS NULL"))

        if "is_active" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
        elif dialect == "postgresql":
            connection.execute(text("ALTER TABLE users ALTER COLUMN is_active DROP DEFAULT"))
            connection.execute(
                text(
                    "ALTER TABLE users ALTER COLUMN is_active TYPE BOOLEAN "
                    "USING (LOWER(COALESCE(is_active::text, 'true')) IN ('true','t','1','yes'))"
                )
            )
            connection.execute(text("ALTER TABLE users ALTER COLUMN is_active SET DEFAULT TRUE"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
