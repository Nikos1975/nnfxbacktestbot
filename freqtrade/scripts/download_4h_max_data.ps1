# Download maximum practical 4h spot data.
# Run from: D:\_projects\trading\freqtrade

docker compose run --rm freqtrade download-data `
  --exchange binance `
  --pairs BTC/USDT ETH/USDT SOL/USDT `
  --timeframes 4h `
  --timerange 20170101- `
  --trading-mode spot
