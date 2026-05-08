from pydantic import BaseModel, Field

class RegimeConfig(BaseModel):
    adx_period: int = 14
    chop_period: int = 14
    active_adx_max: float = 20
    transition_adx_min: float = 20
    transition_adx_max: float = 25
    chop_active_min: float = 61.8
    chop_pause_max: float = 38.2

class GridConfig(BaseModel):
    symbol: str
    timeframe: str
    initial_cash: float = Field(gt=0)
    lower_bound: float = Field(gt=0)
    upper_bound: float = Field(gt=0)
    grid_count: int = Field(ge=2)
    order_size_quote: float = Field(gt=0)
    fee_rate: float = Field(ge=0)
    slippage_rate: float = Field(ge=0)
    regime: RegimeConfig

    def model_post_init(self, __context) -> None:
        if self.upper_bound <= self.lower_bound:
            raise ValueError("upper_bound must be greater than lower_bound")
