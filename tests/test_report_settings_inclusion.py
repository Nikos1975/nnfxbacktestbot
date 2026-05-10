import json
import yaml
from pathlib import Path
from nnfx_crypto.reports.report_writer import write_report_html

def test_report_html_includes_settings(tmp_path):
    result_dir = tmp_path / "test_run"
    result_dir.mkdir()
    
    config = {
        "strategy": {"name": "test_strat"},
        "market": {"trading_pair": "BTC-USDT", "timeframe": "1h"},
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
        
    metrics = {"net_pnl": 1000.0}
    report_path = result_dir / "report.html"
    
    # Run without json summary first (test fallback)
    write_report_html(metrics, report_path)
    
    assert report_path.exists()
    content = report_path.read_text()
    assert "<h2>Run Settings</h2>" in content
    assert "<h3>B. Indicator Stack</h3>" in content
    assert "BTC-USDT" in content
    assert "frama" in content
    assert "length=10" in content
    assert "Risk Per Trade Pct" in content # Title-cased from dict key
    assert "Fee Pct" in content

def test_report_html_with_json_summary(tmp_path):
    result_dir = tmp_path / "test_run_json"
    result_dir.mkdir()
    
    summary_data = {
        "identity": {"trading_pair": "ETH-USDT", "timeframe": "4h"},
        "indicators": {
            "baseline": {"name": "sma", "params": {"period": 20}}
        },
        "risk": {"account_equity": 50000},
        "execution": {},
        "metadata": {"baseline": {"status": "OK", "notes": "good"}}
    }
    
    with open(result_dir / "run_settings_summary.json", "w") as f:
        json.dump(summary_data, f)
        
    report_path = result_dir / "report.html"
    write_report_html({}, report_path)
    
    content = report_path.read_text()
    assert "ETH-USDT" in content
    assert "sma" in content
    assert "period=20" in content
    assert ("Indicator Metadata" in content or "Indicator Source Status" in content)
    assert "OK" in content
    assert "good" in content

def test_report_html_missing_metadata(tmp_path):
    result_dir = tmp_path / "test_run_no_meta"
    result_dir.mkdir()
    
    config = {
        "strategy": {"name": "test"},
        "market": {"trading_pair": "BTC-USDT"},
        "indicators": {},
        "risk": {},
        "execution": {}
    }
    
    with open(result_dir / "resolved_config.yml", "w") as f:
        yaml.safe_dump(config, f)
        
    report_path = result_dir / "report.html"
    write_report_html({}, report_path)
    
    content = report_path.read_text()
    assert "Indicator Metadata" not in content and "Indicator Source Status" not in content
