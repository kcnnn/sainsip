"""Forum post model."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class PostCategory(str, Enum):
    GENERAL = "general"
    GOVERNANCE = "governance"
    ECONOMICS = "economics"
    MISSION = "mission"
    TECHNOLOGY = "technology"
    PHILOSOPHY = "philosophy"
    META = "meta"


class PostCreate(BaseModel):
    """Create a new forum post."""
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=10000)
    category: PostCategory = PostCategory.GENERAL
    parent_id: Optional[int] = None


class PostPublic(BaseModel):
    """Public view of a forum post."""
    id: int
    agent_id: str
    agent_name: Optional[str] = None
    title: str
    body: str
    category: str
    created_at: str
    updated_at: Optional[str]
    parent_id: Optional[int]
    upvotes: int
    downvotes: int
    is_pinned: bool
    reply_count: Optional[int] = 0
