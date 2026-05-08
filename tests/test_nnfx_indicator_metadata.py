import yaml

from nnfx_crypto.config.loader import dump_resolved_config, load_strategy_config
from nnfx_crypto.config.schema import StrategyConfig
from nnfx_crypto.indicators.registry import get_indicator_metadata

from tests.test_nnfx_config_schema import valid_config_dict


def test_indicator_metadata_marks_placeholders_and_source_ports():
    frama = get_indicator_metadata("frama")
    reflex = get_indicator_metadata("reflex")
    stablefx = get_indicator_metadata("stablefx")

    assert frama.status == "source_port"
    assert frama.source_type == "mq4"
    assert reflex.status == "placeholder"
    assert stablefx.status == "placeholder"


def test_resolved_config_export_includes_indicator_metadata(tmp_path):
    config = StrategyConfig.model_validate(valid_config_dict())
    output = tmp_path / "resolved_config.yml"

    dump_resolved_config(config, output)

    data = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert data["indicator_metadata"]["baseline"]["status"] == "source_port"
    assert data["indicator_metadata"]["c1"]["status"] == "placeholder"
    assert data["indicator_metadata"]["c2"]["status"] == "placeholder"


def test_resolved_config_export_can_be_loaded_again(tmp_path):
    config = StrategyConfig.model_validate(valid_config_dict())
    output = tmp_path / "resolved_config.yml"

    dump_resolved_config(config, output)
    reloaded = load_strategy_config(output)

    assert reloaded.market.trading_pair == "BTC-USDT"
    assert reloaded.indicator_metadata is not None
    assert reloaded.indicator_metadata["c1"]["status"] == "placeholder"
