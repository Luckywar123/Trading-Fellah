from pydantic import BaseModel, Field


class NonceRequest(BaseModel):
    wallet: str


class VerifyRequest(BaseModel):
    wallet: str
    signature: str


class LinkMT5AccountRequest(BaseModel):
    label: str = "Main Account"
    broker_server: str = Field(..., description="Contoh: VantageInternational-Live 3")
    mt5_login: str
    mt5_password: str
    is_live: bool = False


class OpenOrderRequest(BaseModel):
    symbol: str
    direction: str = Field(..., pattern="^(LONG|SHORT)$")
    volume_lots: float | None = None          # kalau None -> dihitung otomatis dari risk settings
    stop_loss: float | None = None
    take_profit: float | None = None
    comment: str = "manual"


class RiskSettingsUpdate(BaseModel):
    preset: str | None = None                  # conservative | balanced | aggressive | full_send | custom
    max_margin_pct_per_trade: float | None = None
    max_risk_pct_per_trade: float | None = None
    max_open_positions: int | None = None
    max_daily_trades: int | None = None
    sl_atr_multiplier: float | None = None
    trailing_enabled: bool | None = None
    trailing_trigger_pips: int | None = None
    trail_distance_pips: int | None = None
    news_blackout_enabled: bool | None = None
    news_blackout_minutes: int | None = None
    full_margin_mode: bool | None = None
    ai_confidence_threshold: float | None = None


class BacktestRequest(BaseModel):
    mt5_account_id: str
    symbol: str
    timeframe: str = "15m"
    date_from: str
    date_to: str
    risk_preset: str = "balanced"
    starting_equity: float = 1000.0


class CheckoutRequest(BaseModel):
    plan: str = Field(..., pattern="^(basic|pro|elite)$")
    success_url: str
    cancel_url: str


class KnowledgeItemRequest(BaseModel):
    title: str
    content: str
    tags: list[str] = []
