# Payment API

FastAPI payment service with JWT authentication, users, orders, and wallet operations.

## What Was Updated

- Added production-style JWT auth flow:
  - `POST /auth/signup`
  - `POST /auth/signin`
- Signin supports both:
  - JSON body (`email`, `password`) for API clients
  - OAuth form (`username`, `password`) for Swagger Authorize
- Added structured logging:
  - App startup/shutdown logs
  - Request logs with request ID
  - Route/service success and failure logs
- Added stronger DB behavior:
  - User uniqueness checks (`user_id`, `email`)
  - Passwords stored as `password_hash` only (bcrypt)
  - Wallet operations use row-level lock patterns
- Converted scenario and seed scripts to async (`httpx` + `asyncio`)
- Added graceful script behavior when API server is not running
- Test suite validated: `6 passed`

## Tech Stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic v2
- python-jose (JWT)
- passlib + bcrypt

## Setup

## 1. Create virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Configure environment

Create `.env` in project root with:

```env
DATABASE_URL=postgresql+psycopg://postgres:<your_password>@localhost:5432/appdb
JWT_SECRET_KEY=<your_long_random_secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
APP_ENV=development
LOG_LEVEL=INFO
```

## 3. Start API

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## Authentication Flow

1. Signup user:

```http
POST /auth/signup
```

2. Signin and get token:

```http
POST /auth/signin
```

3. Use token in protected APIs:

```http
Authorization: Bearer <access_token>
```

Protected endpoints:
- `/users/*`
- `/orders/*`
- `/wallet/*`

## API Groups

- `auth`: signup/signin
- `users`: get current user data, list current user view
- `orders`: create/list orders for authenticated customer
- `wallet`: credit/debit/get wallet for authenticated customer

## Async Scripts

Both scripts are async now:

- `scripts/seed_data.py`
- `scripts/run_scenarios.py`

They use `httpx.AsyncClient` and `asyncio` to improve I/O throughput for API calls.

### Run seed script

```powershell
python scripts/seed_data.py --all
```

or

```powershell
python scripts/seed_data.py CUST-001
```

### Run scenarios

```powershell
python scripts/run_scenarios.py --scenario orders_retry
python scripts/run_scenarios.py --scenario wallet_concurrency
python scripts/run_scenarios.py --scenario false_success
python scripts/run_scenarios.py --scenario mixed
```

If API is not running, scripts print a clear start-server message instead of crashing.

## Tests

```powershell
.\.venv\Scripts\python -m pytest -q
```

Current status:
- `6 passed`

## Project Structure

```text
payment-api/
  app/
    auth.py
    config.py
    db.py
    logging_config.py
    main.py
    models.py
    routes_auth.py
    routes_orders.py
    routes_users.py
    routes_wallet.py
    schemas.py
    services.py
  scripts/
    run_scenarios.py
    seed_data.py
  sql/
    schema.sql
    seed_data.sql
  tests/
    test_api.py
```

## Notes for Explanation

If asked why async scripts were used:

"These scripts are network I/O heavy. Async lets multiple HTTP calls run concurrently with lower overhead than threads, so scenario execution is faster and more scalable."
