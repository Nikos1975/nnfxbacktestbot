from pathlib import Path

from nnfx_crypto.config.loader import load_portfolio_config, load_strategy_config


def test_portfolio_algo5_covers_three_pairs_and_three_timeframes():
    portfolio = load_portfolio_config("configs/nnfx_crypto/portfolio_algo5.yml")
    configs = [load_strategy_config(path) for path in portfolio.portfolio.strategies]

    pairs = {config.market.trading_pair for config in configs}
    timeframes = {config.market.timeframe for config in configs}
    combinations = {(config.market.trading_pair, config.market.timeframe) for config in configs}

    assert pairs == {"BTC-USDT", "ETH-USDT", "SOL-USDT"}
    assert timeframes == {"1h", "4h", "1d"}
    assert len(combinations) == 9
    assert len(portfolio.portfolio.strategies) == 9

    for strategy_path in portfolio.portfolio.strategies:
        assert Path(strategy_path).exists()
