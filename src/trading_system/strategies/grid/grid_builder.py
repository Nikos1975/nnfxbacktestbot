import numpy as np
from trading_system.strategies.grid.grid_config import GridConfig

def build_grid_levels(cfg: GridConfig) -> list[float]:
    return np.linspace(cfg.lower_bound, cfg.upper_bound, cfg.grid_count).round(8).tolist()
