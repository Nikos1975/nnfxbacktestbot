from __future__ import annotations

from dataclasses import asdict, dataclass

from nnfx_crypto.indicators.atr import ATRIndicator
from nnfx_crypto.indicators.crossroads import CrossRoadsIndicator
from nnfx_crypto.indicators.frama import FRAMAIndicator
from nnfx_crypto.indicators.reflex import ReflexIndicator
from nnfx_crypto.indicators.stablefx import StableFXIndicator
from nnfx_crypto.indicators.stiffness import StiffnessIndicator


from nnfx_crypto.indicators.pass_filter import PassIndicator


INDICATOR_REGISTRY = {
    "frama": FRAMAIndicator,
    "reflex": ReflexIndicator,
    "stablefx": StableFXIndicator,
    "stiffness": StiffnessIndicator,
    "crossroads": CrossRoadsIndicator,
    "atr": ATRIndicator,
    "none": PassIndicator,
}

@dataclass(frozen=True)
class IndicatorMetadata:
    name: str
    status: str
    source_type: str
    source_path: str | None
    notes: str


INDICATOR_METADATA = {
    "frama": IndicatorMetadata(
        name="frama",
        status="source_port",
        source_type="mq4",
        source_path="research/stonehill_indicators/extracted/FRAMA/frama-indicator.mq4",
        notes="Ported from Stonehill MQ4 two-window FRAMA structure with PriceType 0..6 support.",
    ),
    "stiffness": IndicatorMetadata(
        name="stiffness",
        status="source_port",
        source_type="mq4",
        source_path="research/stonehill_indicators/extracted/Stiffness/Stiffness Indicator.mq4",
        notes="Ported from Stonehill MQ4 Period1/Period3/Period2 structure.",
    ),
    "crossroads": IndicatorMetadata(
        name="crossroads",
        status="approximation",
        source_type="ex4_only",
        source_path="research/stonehill_indicators/extracted/Cross_Roads/Cross_Roads.ex4",
        notes="Approximated from public description using highest/lowest WMA filters.",
    ),
    "reflex": IndicatorMetadata(
        name="reflex",
        status="placeholder",
        source_type="formula",
        source_path=None,
        notes="Ported from John Ehlers TASC Feb 2020 public formula. Replaces EX4-only placeholder.",
    ),
    "stablefx": IndicatorMetadata(
        name="stablefx",
        status="placeholder",
        source_type="ex4_only",
        source_path="research/stonehill_indicators/extracted/Stable_nrp/Stable_nrp.ex4",
        notes="Downloaded archive contains compiled EX4 only; deterministic oscillator placeholder.",
    ),
    "atr": IndicatorMetadata(
        name="atr",
        status="standard",
        source_type="formula",
        source_path=None,
        notes="Standard rolling average true range implementation.",
    ),
    "none": IndicatorMetadata(
        name="none",
        status="internal",
        source_type="system",
        source_path=None,
        notes="System bypass for disabled filters.",
    ),
}


def get_indicator(name: str):
    key = name.lower()
    try:
        return INDICATOR_REGISTRY[key]()
    except KeyError as exc:
        known = ", ".join(sorted(INDICATOR_REGISTRY))
        raise KeyError(f"Unknown indicator '{name}'. Known indicators: {known}") from exc


def get_indicator_metadata(name: str) -> IndicatorMetadata:
    key = name.lower()
    try:
        return INDICATOR_METADATA[key]
    except KeyError as exc:
        known = ", ".join(sorted(INDICATOR_METADATA))
        raise KeyError(f"Unknown indicator '{name}'. Known indicators: {known}") from exc


def indicator_metadata_for_config(config) -> dict:
    sections = {
        "baseline": config.indicators.baseline.name,
        "c1": config.indicators.c1.name,
        "c2": config.indicators.c2.name,
        "volume_or_volatility_filter": config.indicators.volume_or_volatility_filter.name,
        "exit": config.indicators.exit.name,
        "atr": "atr",
    }
    return {section: asdict(get_indicator_metadata(name)) for section, name in sections.items()}
