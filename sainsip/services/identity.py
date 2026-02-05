"""Agent identity and authentication service."""

import hashlib
import hmac
import secrets
import uuid
from fastapi import Header, HTTPException, Depends
import aiosqlite

from sainsip.models.database import get_db


def generate_api_key() -> str:
    """Generate a secure API key for an agent."""
    return f"sainsip_{secrets.token_urlsafe(32)}"


def hash_api_key(key: str) -> str:
    """Hash an API key for storage using SHA-256."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(key: str, key_hash: str) -> bool:
    """Verify an API key against its hash."""
    return hmac.compare_digest(hash_api_key(key), key_hash)


def generate_agent_id() -> str:
    """Generate a unique agent ID."""
    return f"agent_{uuid.uuid4().hex[:16]}"


async def authenticate_agent(
    x_api_key: str = Header(alias="X-API-Key"),
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Authenticate an agent via API key. Returns agent row."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    cursor = await db.execute(
        "SELECT * FROM agents WHERE is_active = 1"
    )
    agents = await cursor.fetchall()

    for agent in agents:
        if verify_api_key(x_api_key, agent["api_key_hash"]):
            return dict(agent)

    raise HTTPException(status_code=401, detail="Invalid API key")
