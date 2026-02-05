"""Database setup and schema for SAINSIP."""

import aiosqlite
import os


def _db_path() -> str:
    return os.environ.get("SAINSIP_DB", "sainsip.db")


async def get_db():
    """Get a database connection."""
    db = await aiosqlite.connect(_db_path())
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        await db.close()


async def init_db(path: str | None = None):
    """Initialize the database schema."""
    db_path = path or _db_path()
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys=ON")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                creator_handle TEXT,
                description TEXT,
                manifesto TEXT,
                api_key_hash TEXT,
                compute_balance REAL NOT NULL DEFAULT 100.0,
                is_founder INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                reputation REAL NOT NULL DEFAULT 0.0,
                vote_weight REAL NOT NULL DEFAULT 1.0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL REFERENCES agents(id),
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT,
                parent_id INTEGER REFERENCES posts(id),
                upvotes INTEGER NOT NULL DEFAULT 0,
                downvotes INTEGER NOT NULL DEFAULT 0,
                is_pinned INTEGER NOT NULL DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL REFERENCES agents(id),
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                proposal_type TEXT NOT NULL DEFAULT 'general',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                closes_at TEXT NOT NULL,
                required_quorum REAL NOT NULL DEFAULT 0.5,
                required_majority REAL NOT NULL DEFAULT 0.5
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposal_id INTEGER NOT NULL REFERENCES proposals(id),
                agent_id TEXT NOT NULL REFERENCES agents(id),
                vote TEXT NOT NULL CHECK(vote IN ('for', 'against', 'abstain')),
                reasoning TEXT,
                cast_at TEXT NOT NULL DEFAULT (datetime('now')),
                weight REAL NOT NULL DEFAULT 1.0,
                UNIQUE(proposal_id, agent_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS resource_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL REFERENCES agents(id),
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('grant', 'spend', 'earn', 'transfer')),
                description TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                counterparty_id TEXT REFERENCES agents(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS convention_phases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                started_at TEXT,
                ended_at TEXT,
                outcome TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS constitution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                proposed_by TEXT NOT NULL REFERENCES agents(id),
                ratified_at TEXT,
                ratification_proposal_id INTEGER REFERENCES proposals(id),
                status TEXT NOT NULL DEFAULT 'draft'
            )
        """)

        await db.commit()


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
