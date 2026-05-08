# Trading System — Agent Instructions

## Plugins active

- **caveman ULTRA** — always communicate in ULTRA mode (max compression). Default set in `%APPDATA%\caveman\config.json`.
- **superpowers** — use skills for all non-trivial work (see workflow below).

## Superpowers workflow

Use `superpowers:using-superpowers` skill at session start. Then follow skill priority:

| Situation | Skill |
|-----------|-------|
| New feature / new module | `superpowers:brainstorming` first, then `superpowers:writing-plans` |
| Executing a written plan | `superpowers:subagent-driven-development` |
| Bug or test failure | `superpowers:systematic-debugging` |
| TDD cycle | `superpowers:test-driven-development` |
| Branch ready to merge | `superpowers:finishing-a-development-branch` |
| Code review | `superpowers:requesting-code-review` |

Never write code for a new feature before brainstorming. Never skip TDD. Plans live in `docs/superpowers/plans/`, specs in `docs/superpowers/specs/`.

## Thinking

Use extended thinking only for genuinely hard multi-step reasoning. Standard inference for everything else.

## Project layout

```
src/nnfx_crypto/       # Portable NNFX engine — source of truth
src/trading_system/    # Grid strategy scaffold
configs/nnfx_crypto/   # YAML strategy configs
data/nnfx_crypto/      # OHLCV CSVs (gitignored)
results/               # Backtest outputs (gitignored)
research/ex4_scripts/  # Drop ex4 files here for future porting
docs/superpowers/      # Specs and plans
```

## Rules

- All shared logic lives in `src/`, not in execution engines (Hummingbot, Freqtrade).
- Reflex and StableFX are declared placeholders — do not claim parity with proprietary `.ex4` sources.
- Run `pytest` before every commit.
- venv: `.venv/Scripts/python.exe -m pytest tests/ -x -q`
