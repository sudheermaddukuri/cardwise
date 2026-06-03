from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class Rewards(BaseModel):
    travel: Optional[str] = None
    dining: Optional[str] = None
    groceries: Optional[str] = None
    gas: Optional[str] = None
    streaming: Optional[str] = None
    special: Optional[str] = None
    other: str = "1x"


class Card(BaseModel):
    id: str
    name: str
    issuer: str
    network: str
    annual_fee: int = 0
    sign_up_bonus: Optional[str] = None
    sign_up_spend: Optional[str] = None
    categories: list[str]
    rewards: Rewards
    perks: list[str] = Field(default_factory=list)
    apply_url: str = "#"
    accent_color: str = "#3b82f6"
