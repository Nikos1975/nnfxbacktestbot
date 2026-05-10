from pathlib import Path
import copy
import yaml

root = Path(r"D:\_projects\trading")

base_candidates = [
    root / "configs/nnfx_crypto/algo5_cross_roads_btc_1d_robust_candidate.yml",
    root / "configs/nnfx_crypto/algo5_cross_roads_btc_1d_variant_b_balanced.yml",
    root / "configs/nnfx_crypto/algo5_cross_roads_btc_1d_variant_b_filter_off.yml",
]

base_path = next((p for p in base_candidates if p.exists()), None)
if base_path is None:
    raise FileNotFoundError("No base config found.")

out_dir = root / "configs/nnfx_crypto/generated/new_indicator_diagnostics"
out_dir.mkdir(parents=True, exist_ok=True)

with base_path.open("r", encoding="utf-8") as f:
    base = yaml.safe_load(f)

def set_common(cfg):
    cfg["strategy"]["direction_mode"] = "both"
    cfg["risk"]["stop_loss_atr_multiplier"] = 1.25
    cfg["risk"]["tp1_atr_multiplier"] = 1.0
    cfg["risk"]["move_second_half_to_breakeven_after_tp1"] = True
    return cfg

def variant(name, c1, c2, vol, exit_):
    cfg = copy.deepcopy(base)
    cfg = set_common(cfg)
    cfg["strategy"]["name"] = f"new_indicator_{name.lower()}"
    cfg["indicators"]["c1"] = c1
    cfg["indicators"]["c2"] = c2
    cfg["indicators"]["volume_or_volatility_filter"] = vol
    cfg["indicators"]["exit"] = exit_
    return cfg

reflex16 = {"name": "reflex", "params": {"length": 16}}
crossroads24_c2 = {"name": "crossroads", "params": {"start_len": 1, "lookback_period": 24, "source": "close"}}
crossroads24_exit = {"name": "crossroads", "params": {"start_len": 2, "lookback_period": 24, "source": "close"}}
none_filter = {"name": "none", "params": {}}
rvol08 = {"name": "rvol", "params": {"length": 20, "threshold": 0.8}}
rvol10 = {"name": "rvol", "params": {"length": 20, "threshold": 1.0}}
ptl_exit = {"name": "perfect_trend_line", "params": {"period": 10, "atr_length": 14, "atr_multiplier": 2.0, "source": "close"}}

zl_standard = {"name": "zero_lag_macd", "params": {"fast_length": 12, "slow_length": 26, "signal_length": 9, "source": "close"}}
zl_fast = {"name": "zero_lag_macd", "params": {"fast_length": 8, "slow_length": 21, "signal_length": 5, "source": "close"}}
zl_daily_supplied = {"name": "zero_lag_macd", "params": {"fast_length": 53, "slow_length": 3, "signal_length": 57, "source": "close"}}
zl_daily_normalized = {"name": "zero_lag_macd", "params": {"fast_length": 3, "slow_length": 53, "signal_length": 57, "source": "close"}}

variants = {
    "A_current_robust_baseline": variant("A", reflex16, crossroads24_c2, none_filter, crossroads24_exit),
    "B_rvol_20_08": variant("B", reflex16, crossroads24_c2, rvol08, crossroads24_exit),
    "C_rvol_20_10": variant("C", reflex16, crossroads24_c2, rvol10, crossroads24_exit),
    "D_perfect_trend_line_exit": variant("D", reflex16, crossroads24_c2, none_filter, ptl_exit),

    "E_zlmacd_standard_c1": variant("E", zl_standard, crossroads24_c2, none_filter, crossroads24_exit),
    "F_zlmacd_fast_c1": variant("F", zl_fast, crossroads24_c2, none_filter, crossroads24_exit),
    "G_zlmacd_daily_supplied_c1": variant("G", zl_daily_supplied, crossroads24_c2, none_filter, crossroads24_exit),
    "H_zlmacd_daily_normalized_c1": variant("H", zl_daily_normalized, crossroads24_c2, none_filter, crossroads24_exit),

    "I_zlmacd_standard_c2": variant("I", reflex16, zl_standard, none_filter, crossroads24_exit),
    "J_zlmacd_fast_c2": variant("J", reflex16, zl_fast, none_filter, crossroads24_exit),
    "K_zlmacd_daily_supplied_c2": variant("K", reflex16, zl_daily_supplied, none_filter, crossroads24_exit),
    "L_zlmacd_daily_normalized_c2": variant("L", reflex16, zl_daily_normalized, none_filter, crossroads24_exit),

    "M_combined_conservative": variant("M", reflex16, zl_standard, rvol08, ptl_exit),
    "N_combined_fast_zlmacd": variant("N", zl_fast, crossroads24_c2, rvol08, ptl_exit),
    "O_combined_daily_supplied_c1": variant("O", zl_daily_supplied, crossroads24_c2, rvol08, ptl_exit),
    "P_combined_daily_normalized_c1": variant("P", zl_daily_normalized, crossroads24_c2, rvol08, ptl_exit),
}

for i, (name, cfg) in enumerate(variants.items(), start=1):
    path = out_dir / f"{i:02d}_{name}.yml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)

print(f"Base config: {base_path}")
print(f"Wrote {len(variants)} configs to: {out_dir}")
