# NNFX Algo5 Hummingbot V2 Dry-Run Notes

Portable logic lives in `src/nnfx_crypto/`. Hummingbot-specific code is isolated under:

```text
src/nnfx_crypto/hummingbot/
  controllers/nnfx_algo5_controller.py
  adapters/hummingbot_config_adapter.py
  adapters/executor_action_adapter.py
```

Example controller config:

```text
configs/nnfx_crypto/hummingbot_nnfx_algo5_controller.yml
```

## Install Shape

When a real Hummingbot V2 checkout is available, copy or package:

```text
src/nnfx_crypto/
```

so it is importable by the Python environment that runs `v2_with_controllers.py`.

Then place or reference:

```text
src/nnfx_crypto/hummingbot/controllers/nnfx_algo5_controller.py
```

as the controller wrapper.

## Validation Steps

1. Confirm Hummingbot imports work in the same environment:

```powershell
python -c "import hummingbot.strategy_v2.controllers.directional_trading_controller_base"
```

2. Confirm portable engine imports:

```powershell
python -c "from nnfx_crypto.signals.nnfx_signal_engine import NNFXSignalEngine"
```

3. Load the config through the adapter:

```powershell
python -c "from nnfx_crypto.hummingbot.adapters.hummingbot_config_adapter import hummingbot_yaml_to_strategy_config; print(hummingbot_yaml_to_strategy_config('configs/nnfx_crypto/hummingbot_nnfx_algo5_controller.yml').market.trading_pair)"
```

4. Run Hummingbot with `v2_with_controllers.py` and the controller config.

## Current Limitation

This repository does not include Hummingbot V2 source. The wrapper is tested with pure-Python
adapter tests, but final `ExecutorAction` class compatibility must be validated inside the
target Hummingbot version.

