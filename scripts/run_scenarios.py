#!/usr/bin/env python3
import argparse
import asyncio
import random
import time

import httpx


class ScenarioRunner:
    def __init__(self, base_url: str, customer_id: str):
        self.base_url = base_url.rstrip("/")
        self.customer_id = customer_id
        self.email = f"{self.customer_id.lower()}@example.com"
        self.password = "Str0ngPassw0rd!"
        self.token: str | None = None

    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    async def ensure_auth(self, client: httpx.AsyncClient) -> None:
        response = await client.post(
            f"{self.base_url}/auth/signup",
            json={
                "user_id": self.customer_id,
                "email": self.email,
                "full_name": f"Test User {self.customer_id}",
                "phone": "+91-9876543210",
                "password": self.password,
            },
        )
        if response.status_code not in (201, 400):
            raise RuntimeError(f"Failed to ensure user: {response.status_code} {response.text}")

        signin = await client.post(
            f"{self.base_url}/auth/signin",
            json={"email": self.email, "password": self.password},
        )
        if signin.status_code != 200:
            suffix = int(time.time())
            self.customer_id = f"CUST-{suffix}"
            self.email = f"{self.customer_id.lower()}@example.com"
            retry_signup = await client.post(
                f"{self.base_url}/auth/signup",
                json={
                    "user_id": self.customer_id,
                    "email": self.email,
                    "full_name": f"Test User {self.customer_id}",
                    "phone": "+91-9876543210",
                    "password": self.password,
                },
            )
            if retry_signup.status_code != 201:
                raise RuntimeError(
                    "Failed to sign in and failed to create fallback user: "
                    f"{retry_signup.status_code} {retry_signup.text}"
                )
            signin = await client.post(
                f"{self.base_url}/auth/signin",
                json={"email": self.email, "password": self.password},
            )
            if signin.status_code != 200:
                raise RuntimeError(f"Failed to sign in: {signin.status_code} {signin.text}")

        self.token = signin.json()["access_token"]

    async def ensure_wallet(self, client: httpx.AsyncClient) -> None:
        print(f"Ensuring user exists for {self.customer_id}...")
        await self.ensure_auth(client)

        print(f"Ensuring wallet exists for {self.customer_id}...")
        response = await client.get(
            f"{self.base_url}/wallet/{self.customer_id}",
            headers=self.auth_headers(),
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Wallet balance: {data['balance']}")
            if data["balance"] < 500:
                print("Topping up wallet...")
                await client.post(
                    f"{self.base_url}/wallet/{self.customer_id}/credit",
                    json={"amount": 1000.0},
                    headers=self.auth_headers(),
                )

    async def orders_retry(self, client: httpx.AsyncClient) -> None:
        print("\n=== Running orders_retry scenario ===")
        await self.ensure_auth(client)

        idempotency_key = f"retry-test-{int(time.time())}"
        order_payload = {
            "customer_id": self.customer_id,
            "amount": 499.99,
            "currency": "INR",
            "idempotency_key": idempotency_key,
        }

        print(f"Attempt 1: Creating order with idempotency_key={idempotency_key}")
        try:
            response1 = await client.post(
                f"{self.base_url}/orders",
                json=order_payload,
                headers=self.auth_headers(),
                timeout=1.0,
            )
            print(f"Attempt 1 response: {response1.status_code} - {response1.json()}")
        except httpx.TimeoutException:
            print("Attempt 1: Request timed out")

        print("\nAttempt 2: Retrying same order...")
        try:
            response2 = await client.post(
                f"{self.base_url}/orders",
                json=order_payload,
                headers=self.auth_headers(),
                timeout=5.0,
            )
            print(f"Attempt 2 response: {response2.status_code} - {response2.json()}")
        except httpx.TimeoutException:
            print("Attempt 2: Request timed out")

        await asyncio.sleep(1)

        print(f"\nFetching all orders for {self.customer_id}...")
        response = await client.get(
            f"{self.base_url}/orders?customer_id={self.customer_id}",
            headers=self.auth_headers(),
        )
        orders = response.json()

        matching_orders = [o for o in orders if o.get("idempotency_key") == idempotency_key]
        print(f"Orders with idempotency_key={idempotency_key}: {len(matching_orders)}")
        for order in matching_orders:
            print(f"  - Order ID: {order['id']}, Amount: {order['amount']}")

    async def wallet_concurrency(self, client: httpx.AsyncClient) -> None:
        print("\n=== Running wallet_concurrency scenario ===")
        await self.ensure_wallet(client)

        print("\nSetting up wallet with known balance...")
        await client.post(
            f"{self.base_url}/wallet/{self.customer_id}/credit",
            json={"amount": 500.0},
            headers=self.auth_headers(),
        )

        await asyncio.sleep(0.5)

        initial_response = await client.get(
            f"{self.base_url}/wallet/{self.customer_id}",
            headers=self.auth_headers(),
        )
        initial_balance = initial_response.json()["balance"]
        print(f"Starting balance: {initial_balance}")

        num_operations = 25
        debit_amount = 10.0
        print(f"\nExecuting {num_operations} concurrent debits of {debit_amount} each...")

        async def debit_operation() -> bool:
            try:
                response = await client.post(
                    f"{self.base_url}/wallet/{self.customer_id}/debit",
                    json={"amount": debit_amount},
                    headers=self.auth_headers(),
                )
                return response.status_code == 200
            except Exception:
                return False

        results = await asyncio.gather(*[debit_operation() for _ in range(num_operations)])
        successful = sum(results)
        print(f"Successful operations: {successful}/{num_operations}")

        await asyncio.sleep(0.5)

        final_response = await client.get(
            f"{self.base_url}/wallet/{self.customer_id}",
            headers=self.auth_headers(),
        )
        final_balance = final_response.json()["balance"]

        expected_balance = initial_balance - (successful * debit_amount)

        print(f"\nInitial balance: {initial_balance}")
        print(f"Expected final balance: {expected_balance}")
        print(f"Actual final balance: {final_balance}")
        print(f"Difference: {abs(expected_balance - final_balance)}")

    async def false_success(self, client: httpx.AsyncClient) -> None:
        print("\n=== Running false_success scenario ===")
        await self.ensure_auth(client)

        invalid_payload = {
            "customer_id": self.customer_id,
            "amount": 0,
            "currency": "INR",
            "idempotency_key": f"invalid-{int(time.time())}",
        }

        print("Creating order with amount=0 (violates constraint)...")
        response = await client.post(
            f"{self.base_url}/orders",
            json=invalid_payload,
            headers=self.auth_headers(),
        )

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")

        await asyncio.sleep(0.5)

        print("\nVerifying order persistence...")
        orders_response = await client.get(
            f"{self.base_url}/orders?customer_id={self.customer_id}",
            headers=self.auth_headers(),
        )
        orders = orders_response.json()

        matching = [o for o in orders if o.get("idempotency_key") == invalid_payload["idempotency_key"]]
        print(f"Orders found with idempotency_key={invalid_payload['idempotency_key']}: {len(matching)}")

        if len(matching) == 0:
            print("Order was not persisted in database")
        else:
            print(f"Order found: {matching[0]}")

    async def mixed(self, client: httpx.AsyncClient) -> None:
        print("\n=== Running mixed scenario ===")
        await self.ensure_wallet(client)

        operations = [
            ("credit", 200.0),
            ("order", 150.0),
            ("debit", 50.0),
            ("order", 300.0),
            ("credit", 100.0),
        ]
        random.shuffle(operations)

        for op_type, amount in operations:
            if op_type == "credit":
                print(f"\nCrediting {amount}...")
                await client.post(
                    f"{self.base_url}/wallet/{self.customer_id}/credit",
                    json={"amount": amount},
                    headers=self.auth_headers(),
                )
            elif op_type == "debit":
                print(f"\nDebiting {amount}...")
                await client.post(
                    f"{self.base_url}/wallet/{self.customer_id}/debit",
                    json={"amount": amount},
                    headers=self.auth_headers(),
                )
            elif op_type == "order":
                print(f"\nCreating order for {amount}...")
                await client.post(
                    f"{self.base_url}/orders",
                    json={
                        "customer_id": self.customer_id,
                        "amount": amount,
                        "currency": "INR",
                    },
                    headers=self.auth_headers(),
                    timeout=5.0,
                )
            await asyncio.sleep(0.2)

        print("\n=== Final state ===")
        wallet = (
            await client.get(
                f"{self.base_url}/wallet/{self.customer_id}",
                headers=self.auth_headers(),
            )
        ).json()
        print(f"Wallet balance: {wallet['balance']}")

        orders = (
            await client.get(
                f"{self.base_url}/orders?customer_id={self.customer_id}",
                headers=self.auth_headers(),
            )
        ).json()
        print(f"Total orders: {len(orders)}")


async def check_server(client: httpx.AsyncClient, base_url: str) -> bool:
    try:
        response = await client.get(f"{base_url.rstrip('/')}/health", timeout=3.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Run API test scenarios")
    parser.add_argument(
        "--scenario",
        default="all",
        choices=["orders_retry", "wallet_concurrency", "false_success", "mixed", "all"],
        help="Scenario to run",
    )
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--customer-id", default="CUST-001", help="Customer ID to use")
    parser.add_argument("--seed", action="store_true", help="Seed initial data")
    parser.add_argument("--repeat", type=int, default=1, help="Number of times to repeat the scenario")

    args = parser.parse_args()
    runner = ScenarioRunner(args.base_url, args.customer_id)

    scenarios = {
        "orders_retry": runner.orders_retry,
        "wallet_concurrency": runner.wallet_concurrency,
        "false_success": runner.false_success,
        "mixed": runner.mixed,
        "all": runner.mixed,
    }

    async with httpx.AsyncClient() as client:
        if not await check_server(client, args.base_url):
            print(
                f"API server is not reachable at {args.base_url}.\n"
                "Start server first:\n"
                "  .\\.venv\\Scripts\\python -m uvicorn app.main:app --port 8000"
            )
            return

        if args.seed:
            await runner.ensure_wallet(client)

        for i in range(args.repeat):
            if args.repeat > 1:
                print(f"\n{'='*60}")
                print(f"Iteration {i+1}/{args.repeat}")
                print(f"{'='*60}")

            await scenarios[args.scenario](client)

            if i < args.repeat - 1:
                await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(async_main())
