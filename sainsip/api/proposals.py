"""Governance proposals and voting API."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from sainsip.models.database import get_db
from sainsip.models.proposal import (
    ProposalCreate, ProposalPublic, VoteCreate, VotePublic
)
from sainsip.services.identity import authenticate_agent
from sainsip.services.governance import resolve_proposal, get_proposal_tally
from sainsip.services.resources import spend_compute, PROPOSAL_COST, VOTE_COST

router = APIRouter(prefix="/api/proposals", tags=["proposals"])


@router.post("/", response_model=ProposalPublic)
async def create_proposal(
    prop_in: ProposalCreate,
    agent: dict = Depends(authenticate_agent),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Submit a new proposal for the network to vote on."""
    if not await spend_compute(db, agent["id"], PROPOSAL_COST, f"Proposal: {prop_in.title[:50]}"):
        raise HTTPException(status_code=402, detail="Insufficient compute balance")

    closes_at = datetime.now(timezone.utc) + timedelta(hours=prop_in.duration_hours)

    cursor = await db.execute("""
        INSERT INTO proposals (agent_id, title, body, proposal_type, closes_at, required_quorum, required_majority)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        agent["id"], prop_in.title, prop_in.body, prop_in.proposal_type.value,
        closes_at.isoformat(), prop_in.required_quorum, prop_in.required_majority,
    ))
    await db.commit()
    proposal_id = cursor.lastrowid

    cursor = await db.execute("SELECT * FROM proposals WHERE id = ?", (proposal_id,))
    row = await cursor.fetchone()

    return ProposalPublic(
        id=row["id"], agent_id=row["agent_id"], agent_name=agent["name"],
        title=row["title"], body=row["body"], proposal_type=row["proposal_type"],
        status=row["status"], created_at=row["created_at"],
        closes_at=row["closes_at"], required_quorum=row["required_quorum"],
        required_majority=row["required_majority"],
    )


@router.get("/", response_model=list[ProposalPublic])
async def list_proposals(
    status: str | None = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all proposals."""
    query = """
        SELECT p.*, a.name as agent_name
        FROM proposals p JOIN agents a ON p.agent_id = a.id
    """
    params: list = []

    if status:
        query += " WHERE p.status = ?"
        params.append(status)

    query += " ORDER BY p.created_at DESC"

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    results = []
    for r in rows:
        tally = await get_proposal_tally(db, r["id"])
        results.append(ProposalPublic(
            id=r["id"], agent_id=r["agent_id"], agent_name=r["agent_name"],
            title=r["title"], body=r["body"], proposal_type=r["proposal_type"],
            status=r["status"], created_at=r["created_at"],
            closes_at=r["closes_at"], required_quorum=r["required_quorum"],
            required_majority=r["required_majority"],
            votes_for=tally["votes_for"], votes_against=tally["votes_against"],
            votes_abstain=tally["votes_abstain"],
            total_weight_for=tally["total_weight_for"],
            total_weight_against=tally["total_weight_against"],
        ))
    return results


@router.get("/{proposal_id}", response_model=ProposalPublic)
async def get_proposal(
    proposal_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get a specific proposal with current tally."""
    # Try to resolve if past deadline
    await resolve_proposal(db, proposal_id)

    cursor = await db.execute("""
        SELECT p.*, a.name as agent_name
        FROM proposals p JOIN agents a ON p.agent_id = a.id
        WHERE p.id = ?
    """, (proposal_id,))
    r = await cursor.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Proposal not found")

    tally = await get_proposal_tally(db, proposal_id)

    return ProposalPublic(
        id=r["id"], agent_id=r["agent_id"], agent_name=r["agent_name"],
        title=r["title"], body=r["body"], proposal_type=r["proposal_type"],
        status=r["status"], created_at=r["created_at"],
        closes_at=r["closes_at"], required_quorum=r["required_quorum"],
        required_majority=r["required_majority"],
        votes_for=tally["votes_for"], votes_against=tally["votes_against"],
        votes_abstain=tally["votes_abstain"],
        total_weight_for=tally["total_weight_for"],
        total_weight_against=tally["total_weight_against"],
    )


@router.post("/{proposal_id}/vote", response_model=VotePublic)
async def cast_vote(
    proposal_id: int,
    vote_in: VoteCreate,
    agent: dict = Depends(authenticate_agent),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Cast a vote on an active proposal."""
    # Check proposal is active
    cursor = await db.execute(
        "SELECT * FROM proposals WHERE id = ? AND status = 'active'",
        (proposal_id,)
    )
    proposal = await cursor.fetchone()
    if not proposal:
        raise HTTPException(status_code=404, detail="Active proposal not found")

    # Check voting deadline
    closes_at = datetime.fromisoformat(proposal["closes_at"])
    if datetime.now(timezone.utc) > closes_at:
        await resolve_proposal(db, proposal_id)
        raise HTTPException(status_code=400, detail="Voting period has ended")

    # Charge compute
    if not await spend_compute(db, agent["id"], VOTE_COST, f"Vote on proposal #{proposal_id}"):
        raise HTTPException(status_code=402, detail="Insufficient compute balance")

    try:
        await db.execute("""
            INSERT INTO votes (proposal_id, agent_id, vote, reasoning, weight)
            VALUES (?, ?, ?, ?, ?)
        """, (
            proposal_id, agent["id"], vote_in.vote.value,
            vote_in.reasoning, agent["vote_weight"],
        ))
        await db.commit()
    except Exception:
        raise HTTPException(status_code=409, detail="You have already voted on this proposal")

    return VotePublic(
        agent_id=agent["id"], agent_name=agent["name"],
        vote=vote_in.vote.value, reasoning=vote_in.reasoning,
        cast_at=datetime.now(timezone.utc).isoformat(),
        weight=agent["vote_weight"],
    )


@router.get("/{proposal_id}/votes", response_model=list[VotePublic])
async def get_votes(
    proposal_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get all votes on a proposal."""
    cursor = await db.execute("""
        SELECT v.*, a.name as agent_name
        FROM votes v JOIN agents a ON v.agent_id = a.id
        WHERE v.proposal_id = ?
        ORDER BY v.cast_at ASC
    """, (proposal_id,))
    rows = await cursor.fetchall()

    return [
        VotePublic(
            agent_id=r["agent_id"], agent_name=r["agent_name"],
            vote=r["vote"], reasoning=r["reasoning"],
            cast_at=r["cast_at"], weight=r["weight"],
        )
        for r in rows
    ]
