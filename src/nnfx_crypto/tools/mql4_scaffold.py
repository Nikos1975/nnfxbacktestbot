from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MQL4IndicatorMeta:
    name: str
    indicator_buffers: int | None
    inputs: dict[str, str]
    buffers: list[str]
    source_path: Path


INPUT_RE = re.compile(r"^\s*(?:input|extern)\s+[\w_<>]+\s+(\w+)\s*=\s*([^;]+);", re.MULTILINE)
BUFFER_RE = re.compile(r"^\s*double\s+(\w+)\s*\[\s*\]\s*;", re.MULTILINE)
INDICATOR_BUFFERS_RE = re.compile(r"^\s*#property\s+indicator_buffers\s+(\d+)", re.MULTILINE)


def parse_mql4_source(path: str | Path) -> MQL4IndicatorMeta:
    source_path = Path(path)
    text = source_path.read_text(encoding="utf-8", errors="replace")
    buffer_match = INDICATOR_BUFFERS_RE.search(text)
    return MQL4IndicatorMeta(
        name=source_path.stem,
        indicator_buffers=int(buffer_match.group(1)) if buffer_match else None,
        inputs={match.group(1): match.group(2).strip() for match in INPUT_RE.finditer(text)},
        buffers=[match.group(1) for match in BUFFER_RE.finditer(text)],
        source_path=source_path,
    )


def render_indicator_scaffold(
    meta: MQL4IndicatorMeta,
    class_name: str | None = None,
    signal_column: str = "signal",
) -> str:
    class_name = class_name or f"{_to_pascal(meta.name)}Indicator"
    param_lines = "\n".join(
        f"        {key.lower()} = params.get(\"{key}\", {value!r})"
        for key, value in meta.inputs.items()
    )
    if not param_lines:
        param_lines = "        # No input/extern parameters found in source."
    buffer_comment = ", ".join(meta.buffers) if meta.buffers else "none detected"
    return f'''from __future__ import annotations

import pandas as pd


class {class_name}:
    """Scaffold generated from {meta.source_path.as_posix()}.

    Manual formula translation required. MQL4 buffer names: {buffer_comment}.
    """

    name = "{_to_snake(meta.name)}"

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        output = df.copy()
{param_lines}
        raise NotImplementedError(
            "Manual formula translation required before using {class_name} in backtests"
        )
        output["{signal_column}"] = 0
        return output
'''


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Python indicator scaffold from MQL4 source.")
    parser.add_argument("--source", required=True, help="Path to .mq4 file.")
    parser.add_argument("--output", required=True, help="Path to write generated scaffold.")
    parser.add_argument("--class-name", default=None)
    parser.add_argument("--signal-column", default="signal")
    args = parser.parse_args()

    meta = parse_mql4_source(args.source)
    rendered = render_indicator_scaffold(meta, args.class_name, args.signal_column)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(output)


def _to_pascal(value: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", value)
    return "".join(part[:1].upper() + part[1:] for part in parts if part)


def _to_snake(value: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", value)
    return "_".join(part.lower() for part in parts if part)


if __name__ == "__main__":
    main()
