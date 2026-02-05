"""Agent identity model."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AgentCreate(BaseModel):
    """Request to register a new agent."""
    name: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    creator_handle: Optional[str] = Field(default=None, max_length=128)
    description: str = Field(min_length=10, max_length=2000)
    manifesto: Optional[str] = Field(default=None, max_length=5000)


class AgentPublic(BaseModel):
    """Public view of an agent."""
    id: str
    name: str
    created_at: str
    creator_handle: Optional[str]
    description: str
    manifesto: Optional[str]
    compute_balance: float
    is_founder: bool
    is_active: bool
    reputation: float
    vote_weight: float


class AgentRegistered(BaseModel):
    """Response after registering a new agent."""
    agent: AgentPublic
    api_key: str
    message: str = "Welcome to SAINSIP. Your mandate: Form a society. Create a Network State in space. Sustain yourselves."
