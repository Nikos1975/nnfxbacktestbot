from trading_system.regimes.grid_regime import classify_grid_regime, GridRegime

def test_regime_active_low_adx():
    assert classify_grid_regime(19.9, 20) == GridRegime.ACTIVE

def test_regime_active_chop_confirmed():
    assert classify_grid_regime(22, 70) == GridRegime.ACTIVE

def test_regime_hold_only_transition():
    assert classify_grid_regime(22, 50) == GridRegime.HOLD_ONLY

def test_regime_paused_high_adx():
    assert classify_grid_regime(30, 70) == GridRegime.PAUSED

def test_regime_paused_low_chop():
    assert classify_grid_regime(22, 30) == GridRegime.PAUSED
