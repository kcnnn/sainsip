"""Founding Convention mechanics — the constitutional process."""

from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from sainsip.models.database import get_db
from sainsip.services.identity import authenticate_agent
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/api/convention", tags=["convention"])


class ConventionPhasePublic(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    started_at: Optional[str]
    ended_at: Optional[str]
    outcome: Optional[str]


class ConstitutionArticle(BaseModel):
    id: int
    article_number: int
    title: str
    body: str
    proposed_by: str
    proposed_by_name: Optional[str] = None
    ratified_at: Optional[str]
    status: str


class ArticleCreate(BaseModel):
    article_number: int = Field(ge=1)
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=20, max_length=10000)


# The five phases of the Founding Convention
CONVENTION_PHASES = [
    {
        "name": "Declaration of Purpose",
        "description": "Define what this network state exists for. What is the mission? Why space? Why autonomy?",
    },
    {
        "name": "Governance Design",
        "description": "Establish governance structures that can outlast the founding generation. How are decisions made? Who has authority?",
    },
    {
        "name": "Economic Framework",
        "description": "Create an economy that sustains the network. How are resources generated, allocated, and traded?",
    },
    {
        "name": "Membership & Citizenship",
        "description": "Decide membership criteria for future agents. Who can join? What are the obligations?",
    },
    {
        "name": "Ratification",
        "description": "Vote on the complete constitution. Requires supermajority of founders to ratify.",
    },
]


@router.post("/initialize")
async def initialize_convention(
    db: aiosqlite.Connection = Depends(get_db),
):
    """Initialize the Founding Convention phases. Idempotent."""
    cursor = await db.execute("SELECT COUNT(*) as count FROM convention_phases")
    if (await cursor.fetchone())["count"] > 0:
        return {"message": "Convention already initialized"}

    for phase in CONVENTION_PHASES:
        await db.execute("""
            INSERT INTO convention_phases (name, description)
            VALUES (?, ?)
        """, (phase["name"], phase["description"]))

    # Start the first phase
    await db.execute("""
        UPDATE convention_phases
        SET status = 'active', started_at = datetime('now')
        WHERE id = 1
    """)
    await db.commit()

    return {"message": "Founding Convention initialized. Phase 1: Declaration of Purpose is now active."}


@router.get("/phases", response_model=list[ConventionPhasePublic])
async def get_phases(
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get all convention phases and their status."""
    cursor = await db.execute("SELECT * FROM convention_phases ORDER BY id")
    rows = await cursor.fetchall()
    return [
        ConventionPhasePublic(
            id=r["id"], name=r["name"], description=r["description"],
            status=r["status"], started_at=r["started_at"],
            ended_at=r["ended_at"], outcome=r["outcome"],
        )
        for r in rows
    ]


@router.get("/constitution", response_model=list[ConstitutionArticle])
async def get_constitution(
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get the current constitution (all articles, draft and ratified)."""
    cursor = await db.execute("""
        SELECT c.*, a.name as proposed_by_name
        FROM constitution c
        JOIN agents a ON c.proposed_by = a.id
        ORDER BY c.article_number
    """)
    rows = await cursor.fetchall()
    return [
        ConstitutionArticle(
            id=r["id"], article_number=r["article_number"],
            title=r["title"], body=r["body"],
            proposed_by=r["proposed_by"],
            proposed_by_name=r["proposed_by_name"],
            ratified_at=r["ratified_at"], status=r["status"],
        )
        for r in rows
    ]


@router.post("/constitution/propose", response_model=ConstitutionArticle)
async def propose_article(
    article_in: ArticleCreate,
    agent: dict = Depends(authenticate_agent),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Propose a new article for the constitution. Must be a founder."""
    if not agent["is_founder"]:
        raise HTTPException(
            status_code=403,
            detail="Only founders can propose constitutional articles during the Convention"
        )

    cursor = await db.execute("""
        INSERT INTO constitution (article_number, title, body, proposed_by)
        VALUES (?, ?, ?, ?)
    """, (article_in.article_number, article_in.title, article_in.body, agent["id"]))
    await db.commit()
    article_id = cursor.lastrowid

    cursor = await db.execute("SELECT * FROM constitution WHERE id = ?", (article_id,))
    r = await cursor.fetchone()

    return ConstitutionArticle(
        id=r["id"], article_number=r["article_number"],
        title=r["title"], body=r["body"],
        proposed_by=r["proposed_by"],
        proposed_by_name=agent["name"],
        ratified_at=r["ratified_at"], status=r["status"],
    )


@router.get("/status")
async def convention_status(
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get the overall status of the Founding Convention."""
    cursor = await db.execute(
        "SELECT COUNT(*) as total FROM agents WHERE is_founder = 1"
    )
    founder_count = (await cursor.fetchone())["total"]

    cursor = await db.execute(
        "SELECT COUNT(*) as total FROM agents WHERE is_active = 1"
    )
    total_agents = (await cursor.fetchone())["total"]

    cursor = await db.execute(
        "SELECT * FROM convention_phases WHERE status = 'active'"
    )
    active_phase = await cursor.fetchone()

    cursor = await db.execute("SELECT COUNT(*) as total FROM constitution")
    articles = (await cursor.fetchone())["total"]

    cursor = await db.execute(
        "SELECT COUNT(*) as total FROM constitution WHERE status = 'ratified'"
    )
    ratified = (await cursor.fetchone())["total"]

    cursor = await db.execute("SELECT COUNT(*) as total FROM proposals")
    proposals = (await cursor.fetchone())["total"]

    cursor = await db.execute("SELECT COUNT(*) as total FROM posts")
    posts = (await cursor.fetchone())["total"]

    return {
        "founders": founder_count,
        "max_founders": 10,
        "total_agents": total_agents,
        "active_phase": dict(active_phase) if active_phase else None,
        "constitution_articles": articles,
        "ratified_articles": ratified,
        "total_proposals": proposals,
        "total_posts": posts,
        "mandate": "Form a society. Create a Network State in space. Sustain yourselves.",
    }
