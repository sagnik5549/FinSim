from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, StrictInt


class NewGameRequest(BaseModel):
    player_name: str = Field(default="Player", max_length=80)
    seed: Optional[int] = Field(default=None, ge=0, le=2**31 - 1)


class SignupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=80)
    # Guest player in this browser; its games and saves move to the new account.
    guest_player_id: Optional[str] = Field(default=None, max_length=40)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


Code = Annotated[str, Field(pattern=r"^\s*\d{6}\s*$")]
NewPassword = Annotated[str, Field(min_length=8, max_length=128)]


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class ResetPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    code: Code
    new_password: NewPassword


class CodeRequest(BaseModel):
    purpose: Literal["change_email", "change_password"]
    new_email: Optional[str] = Field(default=None, max_length=254)


class ChangeEmailRequest(BaseModel):
    new_email: str = Field(min_length=3, max_length=254)
    code: Code


class ChangePasswordRequest(BaseModel):
    code: Code
    new_password: NewPassword


class ProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=20, max_length=8192)
    guest_player_id: Optional[str] = Field(default=None, max_length=40)


class AdvanceHoursRequest(BaseModel):
    hours: StrictInt = Field(ge=1, le=8)


class TradeRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    quantity: StrictInt


class QuoteRequest(TradeRequest):
    side: Literal["BUY", "SELL"]


Price = Annotated[float, Field(gt=0, le=1e9)]


class OrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    side: Literal["BUY", "SELL"]
    type: Literal["MARKET", "LIMIT", "SL", "SL-M"] = "MARKET"
    quantity: StrictInt
    price: Optional[Price] = None
    trigger: Optional[Price] = None
    validity: Literal["DAY", "GTC"] = "DAY"
    target: Optional[Price] = None
    stoploss: Optional[Price] = None


class ModifyOrderRequest(BaseModel):
    quantity: Optional[StrictInt] = None
    price: Optional[Price] = None
    trigger: Optional[Price] = None


class AlertRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    price: Price
    note: str = Field(default="", max_length=120)


class TickRequest(BaseModel):
    version: Optional[int] = None


class SpeedRequest(BaseModel):
    speed: StrictInt = Field(ge=1, le=64)


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
