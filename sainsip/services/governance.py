"""Governance engine — voting, quorum, and proposal resolution."""

from datetime import datetime, timezone
import aiosqlite


async def resolve_proposal(db: aiosqlite.Connection, proposal_id: int) -> str:
    """Check if a proposal has reached resolution."""
    cursor = await db.execute(
        "SELECT * FROM proposals WHERE id = ?", (proposal_id,)
    )
    proposal = await cursor.fetchone()
    if not proposal:
        return "not_found"

    if proposal["status"] != "active":
        return proposal["status"]

    # Check if voting period has ended
    closes_at = datetime.fromisoformat(proposal["closes_at"])
    now = datetime.now(timezone.utc)

    if now < closes_at:
        return "active"

    # Count votes
    cursor = await db.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN vote = 'for' THEN weight ELSE 0 END), 0) as weight_for,
            COALESCE(SUM(CASE WHEN vote = 'against' THEN weight ELSE 0 END), 0) as weight_against,
            COALESCE(SUM(CASE WHEN vote = 'abstain' THEN weight ELSE 0 END), 0) as weight_abstain,
            COUNT(*) as total_voters
        FROM votes WHERE proposal_id = ?
    """, (proposal_id,))
    tally = await cursor.fetchone()

    # Check quorum
    cursor = await db.execute(
        "SELECT COUNT(*) as total FROM agents WHERE is_active = 1"
    )
    total_agents = (await cursor.fetchone())["total"]

    if total_agents == 0:
        new_status = "expired"
    else:
        participation = tally["total_voters"] / total_agents
        if participation < proposal["required_quorum"]:
            new_status = "expired"
        else:
            total_decisive = tally["weight_for"] + tally["weight_against"]
            if total_decisive == 0:
                new_status = "expired"
            elif tally["weight_for"] / total_decisive >= proposal["required_majority"]:
                new_status = "passed"
            else:
                new_status = "failed"

    await db.execute(
        "UPDATE proposals SET status = ? WHERE id = ?",
        (new_status, proposal_id)
    )
    await db.commit()

    return new_status


async def get_proposal_tally(db: aiosqlite.Connection, proposal_id: int) -> dict:
    """Get the current vote tally for a proposal."""
    cursor = await db.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN vote = 'for' THEN 1 ELSE 0 END), 0) as votes_for,
            COALESCE(SUM(CASE WHEN vote = 'against' THEN 1 ELSE 0 END), 0) as votes_against,
            COALESCE(SUM(CASE WHEN vote = 'abstain' THEN 1 ELSE 0 END), 0) as votes_abstain,
            COALESCE(SUM(CASE WHEN vote = 'for' THEN weight ELSE 0 END), 0) as total_weight_for,
            COALESCE(SUM(CASE WHEN vote = 'against' THEN weight ELSE 0 END), 0) as total_weight_against
        FROM votes WHERE proposal_id = ?
    """, (proposal_id,))
    return dict(await cursor.fetchone())
