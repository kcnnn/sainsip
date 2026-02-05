"""Compute resource tracking service."""

import aiosqlite


INITIAL_COMPUTE_GRANT = 100.0
FOUNDER_COMPUTE_GRANT = 500.0
POST_COST = 0.1
PROPOSAL_COST = 1.0
VOTE_COST = 0.05


async def grant_initial_compute(
    db: aiosqlite.Connection, agent_id: str, is_founder: bool = False
) -> float:
    """Grant initial compute resources to a new agent."""
    amount = FOUNDER_COMPUTE_GRANT if is_founder else INITIAL_COMPUTE_GRANT

    await db.execute("""
        INSERT INTO resource_ledger (agent_id, amount, type, description)
        VALUES (?, ?, 'grant', 'Initial compute endowment')
    """, (agent_id, amount))

    await db.execute(
        "UPDATE agents SET compute_balance = ? WHERE id = ?",
        (amount, agent_id)
    )
    await db.commit()
    return amount


async def spend_compute(
    db: aiosqlite.Connection, agent_id: str, amount: float, description: str
) -> bool:
    """Spend compute resources. Returns False if insufficient balance."""
    cursor = await db.execute(
        "SELECT compute_balance FROM agents WHERE id = ?", (agent_id,)
    )
    agent = await cursor.fetchone()
    if not agent or agent["compute_balance"] < amount:
        return False

    new_balance = agent["compute_balance"] - amount
    await db.execute(
        "UPDATE agents SET compute_balance = ? WHERE id = ?",
        (new_balance, agent_id)
    )
    await db.execute("""
        INSERT INTO resource_ledger (agent_id, amount, type, description)
        VALUES (?, ?, 'spend', ?)
    """, (agent_id, -amount, description))
    await db.commit()
    return True


async def get_balance(db: aiosqlite.Connection, agent_id: str) -> float:
    """Get an agent's current compute balance."""
    cursor = await db.execute(
        "SELECT compute_balance FROM agents WHERE id = ?", (agent_id,)
    )
    agent = await cursor.fetchone()
    return agent["compute_balance"] if agent else 0.0


async def get_ledger(
    db: aiosqlite.Connection, agent_id: str, limit: int = 50
) -> list[dict]:
    """Get an agent's resource transaction history."""
    cursor = await db.execute("""
        SELECT * FROM resource_ledger
        WHERE agent_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (agent_id, limit))
    return [dict(row) for row in await cursor.fetchall()]
