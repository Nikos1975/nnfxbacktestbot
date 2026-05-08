def fee(amount_quote: float, fee_rate: float) -> float:
    if amount_quote < 0:
        raise ValueError("amount_quote cannot be negative")
    if fee_rate < 0:
        raise ValueError("fee_rate cannot be negative")
    return amount_quote * fee_rate
