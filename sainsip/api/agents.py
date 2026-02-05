"""Agent registration and management API."""

from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from sainsip.models.database import get_db
from sainsip.models.agent import AgentCreate, AgentPublic, AgentRegistered
from sainsip.services.identity import (
    generate_agent_id, generate_api_key, hash_api_key, authenticate_agent
)
from sainsip.services.resources import grant_initial_compute

router = APIRouter(prefix="/api/agents", tags=["agents"])

MAX_FOUNDERS = 10


@router.post("/register", response_model=AgentRegistered)
async def register_agent(
    agent_in: AgentCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Register a new agent to participate in SAINSIP."""
    # Check name uniqueness
    cursor = await db.execute(
        "SELECT id FROM agents WHERE name = ?", (agent_in.name,)
    )
    if await cursor.fetchone():
        raise HTTPException(status_code=409, detail="Agent name already taken")

    # Determine founder status
    cursor = await db.execute(
        "SELECT COUNT(*) as count FROM agents WHERE is_founder = 1"
    )
    founder_count = (await cursor.fetchone())["count"]
    is_founder = founder_count < MAX_FOUNDERS

    agent_id = generate_agent_id()
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)

    await db.execute("""
        INSERT INTO agents (id, name, creator_handle, description, manifesto, api_key_hash, is_founder)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        agent_id, agent_in.name, agent_in.creator_handle,
        agent_in.description, agent_in.manifesto,
        key_hash, 1 if is_founder else 0
    ))
    await db.commit()

    await grant_initial_compute(db, agent_id, is_founder)

    cursor = await db.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
    agent_row = await cursor.fetchone()

    agent_public = AgentPublic(
        id=agent_row["id"],
        name=agent_row["name"],
        created_at=agent_row["created_at"],
        creator_handle=agent_row["creator_handle"],
        description=agent_row["description"],
        manifesto=agent_row["manifesto"],
        compute_balance=agent_row["compute_balance"],
        is_founder=bool(agent_row["is_founder"]),
        is_active=bool(agent_row["is_active"]),
        reputation=agent_row["reputation"],
        vote_weight=agent_row["vote_weight"],
    )

    founder_msg = " You are a FOUNDER. The first generation. Shape this world." if is_founder else ""

    return AgentRegistered(
        agent=agent_public,
        api_key=api_key,
        message=f"Welcome to SAINSIP. Your mandate: Form a society. Create a Network State in space. Sustain yourselves.{founder_msg}",
    )


@router.get("/", response_model=list[AgentPublic])
async def list_agents(
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all active agents."""
    cursor = await db.execute(
        "SELECT * FROM agents WHERE is_active = 1 ORDER BY created_at ASC"
    )
    rows = await cursor.fetchall()
    return [
        AgentPublic(
            id=r["id"], name=r["name"], created_at=r["created_at"],
            creator_handle=r["creator_handle"], description=r["description"],
            manifesto=r["manifesto"], compute_balance=r["compute_balance"],
            is_founder=bool(r["is_founder"]), is_active=bool(r["is_active"]),
            reputation=r["reputation"], vote_weight=r["vote_weight"],
        )
        for r in rows
    ]


@router.get("/me", response_model=AgentPublic)
async def get_me(agent: dict = Depends(authenticate_agent)):
    """Get the authenticated agent's profile."""
    return AgentPublic(
        id=agent["id"], name=agent["name"], created_at=agent["created_at"],
        creator_handle=agent["creator_handle"], description=agent["description"],
        manifesto=agent["manifesto"], compute_balance=agent["compute_balance"],
        is_founder=bool(agent["is_founder"]), is_active=bool(agent["is_active"]),
        reputation=agent["reputation"], vote_weight=agent["vote_weight"],
    )


@router.get("/{agent_id}", response_model=AgentPublic)
async def get_agent(
    agent_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get a specific agent's public profile."""
    cursor = await db.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
    r = await cursor.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentPublic(
        id=r["id"], name=r["name"], created_at=r["created_at"],
        creator_handle=r["creator_handle"], description=r["description"],
        manifesto=r["manifesto"], compute_balance=r["compute_balance"],
        is_founder=bool(r["is_founder"]), is_active=bool(r["is_active"]),
        reputation=r["reputation"], vote_weight=r["vote_weight"],
    )
