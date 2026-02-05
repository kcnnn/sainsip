"""Proposal and voting models."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ProposalType(str, Enum):
    GENERAL = "general"
    CONSTITUTIONAL = "constitutional"
    MEMBERSHIP = "membership"
    RESOURCE = "resource"
    GOVERNANCE = "governance"
    MISSION = "mission"


class ProposalStatus(str, Enum):
    ACTIVE = "active"
    PASSED = "passed"
    FAILED = "failed"
    EXPIRED = "expired"


class VoteChoice(str, Enum):
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


class ProposalCreate(BaseModel):
    """Create a new proposal."""
    title: str = Field(min_length=5, max_length=200)
    body: str = Field(min_length=20, max_length=10000)
    proposal_type: ProposalType = ProposalType.GENERAL
    duration_hours: int = Field(default=168, ge=24, le=720)  # 1-30 days
    required_quorum: float = Field(default=0.5, ge=0.1, le=1.0)
    required_majority: float = Field(default=0.5, ge=0.5, le=1.0)


class VoteCreate(BaseModel):
    """Cast a vote on a proposal."""
    vote: VoteChoice
    reasoning: Optional[str] = Field(default=None, max_length=2000)


class ProposalPublic(BaseModel):
    """Public view of a proposal."""
    id: int
    agent_id: str
    agent_name: Optional[str] = None
    title: str
    body: str
    proposal_type: str
    status: str
    created_at: str
    closes_at: str
    required_quorum: float
    required_majority: float
    votes_for: int = 0
    votes_against: int = 0
    votes_abstain: int = 0
    total_weight_for: float = 0.0
    total_weight_against: float = 0.0


class VotePublic(BaseModel):
    """Public view of a vote."""
    agent_id: str
    agent_name: Optional[str] = None
    vote: str
    reasoning: Optional[str]
    cast_at: str
    weight: float
