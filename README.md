# Forecast Roblox Up-and-Coming Top 10

Entry for make.fun bounty: Predict Roblox's Up-and-Coming top 10.

## What it does

Reads hourly snapshots of Roblox's Up-and-Coming chart from /input,
analyzes game trends, player growth, rank volatility, and momentum,
then forecasts the top 10 for each hour of the 72-hour window.

## Output

Writes `/output/forecast.json` with:
- Top 10 slots with game probabilities at each place
- Game list with probabilities for each position

## Run

```bash
python3 main.py
```

## Requirements

- Python 3.13+
- Standard library only (no external dependencies)
- No network access
- Deterministic output (same input → same output)

## License

MIT
