#!/usr/bin/env python3
"""Test JWT login and RBAC across viewer, analyst, and admin roles."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from httpx import ASGITransport, AsyncClient  # noqa: E402

from backend.app.main import app  # noqa: E402

DEMO_USERS = {
    "viewer": ("viewer@commercialbank.com", "viewer123"),
    "analyst": ("analyst@commercialbank.com", "analyst123"),
    "admin": ("admin@commercialbank.com", "admin123"),
}


async def login(client: AsyncClient, role: str) -> str:
    email, password = DEMO_USERS[role]
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    response.raise_for_status()
    return response.json()["access_token"]


async def search_restricted(client: AsyncClient, token: str) -> list[dict]:
    response = await client.post(
        "/api/v1/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "restricted fraud ring investigation"},
    )
    response.raise_for_status()
    return response.json()["results"]


async def main_async() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for role in ("viewer", "analyst", "admin"):
            token = await login(client, role)
            me = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            me.raise_for_status()
            profile = me.json()
            print(f"{role}: logged in as {profile['email']} ({profile['role']})")

            results = await search_restricted(client, token)
            restricted = [
                r for r in results if r.get("access_level") == "restricted"
            ]
            print(f"  restricted hits: {len(restricted)} / {len(results)}")

        # MCP query as analyst
        analyst_token = await login(client, "analyst")
        chat = await client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"message": "Who owns the payments service?"},
        )
        chat.raise_for_status()
        data = chat.json()
        tool_events = [
            e for e in data.get("agent_events", []) if e.get("node") == "tools"
        ]
        print(f"\nanalyst MCP chat tool events: {[e.get('event_type') for e in tool_events]}")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
