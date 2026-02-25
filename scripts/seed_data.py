#!/usr/bin/env python3
import asyncio
import sys

import httpx

BASE_URL = "http://localhost:8000"
DEFAULT_PASSWORD = "Str0ngPassw0rd!"


async def check_server(client: httpx.AsyncClient) -> bool:
    try:
        response = await client.get(f"{BASE_URL}/health", timeout=3.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def seed_user(
    client: httpx.AsyncClient,
    user_id: str,
    email: str,
    full_name: str,
    phone: str | None = None,
    password: str = DEFAULT_PASSWORD,
) -> bool:
    print(f"Creating user {user_id}...")
    response = await client.post(
        f"{BASE_URL}/auth/signup",
        json={
            "user_id": user_id,
            "email": email,
            "full_name": full_name,
            "phone": phone,
            "password": password,
        },
    )

    if response.status_code == 201:
        data = response.json()
        print(f"✓ User created: {data['user_id']} - {data['full_name']} ({data['email']})")
        return True
    print(f"✗ Failed to create user: {response.status_code}")
    if response.status_code != 404:
        print(f"  {response.text}")
    return False


async def signin(
    client: httpx.AsyncClient, email: str, password: str = DEFAULT_PASSWORD
) -> str | None:
    response = await client.post(
        f"{BASE_URL}/auth/signin",
        json={"email": email, "password": password},
    )
    if response.status_code != 200:
        print(f"Failed to sign in: {response.status_code} {response.text}")
        return None
    return response.json()["access_token"]


async def seed_wallet(
    client: httpx.AsyncClient, customer_id: str, token: str, initial_balance: float = 1000.0
) -> bool:
    print(f"Seeding wallet for {customer_id} with balance {initial_balance}...")
    response = await client.post(
        f"{BASE_URL}/wallet/{customer_id}/credit",
        json={"amount": initial_balance},
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Wallet created: {data['customer_id']} - Balance: {data['balance']}")
        return True
    print(f"✗ Failed to create wallet: {response.status_code}")
    print(f"  {response.text}")
    return False


async def seed_orders(client: httpx.AsyncClient, customer_id: str, token: str, count: int = 3) -> None:
    print(f"\nCreating {count} sample orders for {customer_id}...")
    for i in range(count):
        amount = 100.0 + (i * 50)
        response = await client.post(
            f"{BASE_URL}/orders",
            json={
                "customer_id": customer_id,
                "amount": amount,
                "currency": "INR",
                "idempotency_key": f"seed-order-{customer_id}-{i}",
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        if response.status_code == 201:
            data = response.json()
            print(f"✓ Order created: {data['order_id']}")
        else:
            print(f"✗ Failed to create order: {response.status_code}")


async def seed_multiple_users(client: httpx.AsyncClient) -> None:
    users = [
        ("CUST-001", "john.doe@example.com", "John Doe", "+91-9876543210"),
        ("CUST-002", "jane.smith@example.com", "Jane Smith", "+91-9876543211"),
        ("CUST-003", "bob.wilson@example.com", "Bob Wilson", "+91-9876543212"),
    ]

    print("=" * 60)
    print("Seeding multiple users")
    print("=" * 60)

    for user_id, email, full_name, phone in users:
        print(f"\n--- Processing {user_id} ---")
        if await seed_user(client, user_id, email, full_name, phone):
            token = await signin(client, email)
            if token:
                await seed_wallet(client, user_id, token, 1000.0 + (int(user_id.split("-")[1]) * 500))
                await seed_orders(client, user_id, token, 2)


async def async_main() -> None:
    async with httpx.AsyncClient() as client:
        if not await check_server(client):
            print(
                "API server is not reachable at http://localhost:8000.\n"
                "Start server first:\n"
                "  .\\.venv\\Scripts\\python -m uvicorn app.main:app --port 8000"
            )
            return

        if len(sys.argv) > 1 and sys.argv[1] == "--all":
            await seed_multiple_users(client)
        else:
            customer_id = sys.argv[1] if len(sys.argv) > 1 else "CUST-001"
            email = sys.argv[2] if len(sys.argv) > 2 else f"{customer_id.lower()}@example.com"
            full_name = sys.argv[3] if len(sys.argv) > 3 else "Test User"

            print(f"Starting data seeding for customer: {customer_id}\n")
            if await seed_user(client, customer_id, email, full_name, "+91-9876543210"):
                token = await signin(client, email)
                if token:
                    await seed_wallet(client, customer_id, token, 1000.0)
                    await seed_orders(client, customer_id, token, 3)
            print("\n✓ Seeding complete!")


if __name__ == "__main__":
    asyncio.run(async_main())
