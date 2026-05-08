# Download maximum practical 1h spot data.
# Run from: D:\_projects\trading\freqtrade

docker compose run --rm freqtrade download-data `
  --exchange binance `
  --pairs BTC/USDT ETH/USDT SOL/USDT `
  --timeframes 1h `
  --timerange 20170101- `
  --trading-mode spot
