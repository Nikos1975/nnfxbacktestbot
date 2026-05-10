import json
import yaml
from pathlib import Path
import pytest
from nnfx_crypto.reports.run_settings_writer import write_run_settings_summary

def test_write_run_settings_summary_full(tmp_path):
    result_dir = tmp_path / "test_run"
    result_dir.mkdir()
    
    config = {
        "strategy": {"name": "test_strat"},
        "market": {"trading_pair": "BTC-USDT", "timeframe": "1h"},
        "data": {"path": "test.csv", "start": "2020-01-01", "end": "2020-12-31"},
        "indicators": {
            "baseline": {"name": "frama", "params": {"length": 10}},
            "c2": {"name": "crossroads", "params": {"lookback": 24}}
        },
        "risk": {"risk_per_trade_pct": 0.02},
        "execution": {"fee_pct": 0.0006},
        "indicator_metadata": {"c2": {"status": "valid", "notes": "test notes"}}
    }
    
    with open(result_dir / "resolved_config.yml", "w") as f:
        yaml.safe_dump(config, f)
        
    metrics = {
        "net_pnl": 1000.0,
        "net_pnl_pct": 0.1,
        "total_trades": 50
    }
    with open(result_dir / "metrics.json", "w") as f:
        json.dump(metrics, f)
        
    write_run_settings_summary(result_dir)
    
    # Check JSON
    json_path = result_dir / "run_settings_summary.json"
    assert json_path.exists()
    with open(json_path, "r") as f:
        data = json.load(f)
        assert data["identity"]["strategy_name"] == "test_strat"
        assert data["metrics"]["net_pnl"] == 1000.0
        assert data["indicators"]["baseline"]["name"] == "frama"
        assert data["metadata"]["c2"]["status"] == "valid"

    # Check Markdown
    md_path = result_dir / "run_settings_summary.md"
    assert md_path.exists()
    content = md_path.read_text()
    assert "# Run Settings Summary - test_run" in content
    assert "- **Strategy**: test_strat" in content
    assert "baseline: frama(length=10)" in content
    assert "Net PnL: 1,000.00" in content # Formatted

def test_write_run_settings_summary_missing_metrics(tmp_path):
    result_dir = tmp_path / "test_run_no_metrics"
    result_dir.mkdir()
    
    config = {
        "strategy": {"name": "test_strat"},
        "market": {"trading_pair": "BTC-USDT", "timeframe": "1h"},
        "indicators": {}
    }
    
    with open(result_dir / "resolved_config.yml", "w") as f:
        yaml.safe_dump(config, f)
        
    # No metrics.json
    
    write_run_settings_summary(result_dir)
    
    assert (result_dir / "run_settings_summary.json").exists()
    assert (result_dir / "run_settings_summary.md").exists()
    
    content = (result_dir / "run_settings_summary.md").read_text()
    assert "## E. Key Metrics" not in content # Section should be omitted if no metrics
