# Download maximum practical Daily spot data for NNFX testing.
# Run from: D:\_projects\trading\freqtrade
#
# Notes:
# - Binance spot BTC/USDT and ETH/USDT start in 2017.
# - SOL/USDT starts later; Freqtrade/Binance will download from the first available candle.
# - Open-ended timerange downloads until latest available data.

docker compose run --rm freqtrade download-data `
  --exchange binance `
  --pairs BTC/USDT ETH/USDT SOL/USDT `
  --timeframes 1d `
  --timerange 20170101- `
  --trading-mode spot
