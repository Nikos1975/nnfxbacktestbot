def apply_slippage(price: float, side: str, slippage_rate: float) -> float:
    if slippage_rate < 0:
        raise ValueError("slippage_rate cannot be negative")
    if side == "buy":
        return price * (1 + slippage_rate)
    if side == "sell":
        return price * (1 - slippage_rate)
    raise ValueError("side must be 'buy' or 'sell'")
