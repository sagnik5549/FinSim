from typing import Literal, Optional

from pydantic import BaseModel, Field, StrictInt


class NewGameRequest(BaseModel):
    player_name: str = Field(default="Player", max_length=80)
    seed: Optional[int] = Field(default=None, ge=0, le=2**31 - 1)
    player_id: Optional[str] = None


class AdvanceHoursRequest(BaseModel):
    hours: StrictInt = Field(ge=1, le=8)


class TradeRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    quantity: StrictInt


class QuoteRequest(TradeRequest):
    side: Literal["BUY", "SELL"]


class ResearchRequest(BaseModel):
    depth: Literal["QUICK", "DEEP"] = "QUICK"


class ThesisRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    stance: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    text: str = Field(min_length=3, max_length=500)


class ResolveRiskRequest(BaseModel):
    warning_id: str
    action: Literal["REDUCE_EXPOSURE", "REQUEST_EXCEPTION", "IGNORE"]


class LeaveRequest(BaseModel):
    days: StrictInt = Field(ge=1, le=30)


class AcceptOpportunityRequest(BaseModel):
    quantity: Optional[StrictInt] = None


class SaveRequest(BaseModel):
    name: str = Field(default="Quick save", max_length=80)


class LoadRequest(BaseModel):
    save_id: int


class AckRequest(BaseModel):
    popup_id: str


class ReadRequest(BaseModel):
    kind: Literal["messages", "notifications"]
    ids: Optional[list[str]] = None


class HireRequest(BaseModel):
    candidate_id: str
