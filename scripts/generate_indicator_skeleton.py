import argparse
import json
import sys
from pathlib import Path

# Add scripts to path so we can import inspect_mq4_indicator
sys.path.insert(0, str(Path(__file__).parent))
try:
    from inspect_mq4_indicator import parse_mq4
except ImportError:
    # Fallback if imported differently
    def parse_mq4(c): return {}

TEMPLATE = """from __future__ import annotations

import pandas as pd
from dataclasses import dataclass

from nnfx_crypto.indicators.base import Indicator

@dataclass
class {class_name}Config:
    # TODO: Add parameters here
{params_str}


class {class_name}Indicator(Indicator):
    name = "{indicator_name}"

    def compute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        \"\"\"
        Compute {indicator_name} indicator.
        
        Args:
            df (pd.DataFrame): DataFrame with at least Open, High, Low, Close, Volume columns.
            params (dict): Parameters dictionary conforming to {class_name}Config.
            
        Returns:
            pd.DataFrame: Original DataFrame with appended output columns.
            
        TODOs from MQ4 translation:
        - Output Buffers expected: {buffers_count}
        - Built-in calls detected: {indicator_calls}
        \"\"\"
        df = df.copy()
        
        # Parse params
        config = {class_name}Config(**params)
        
        # TODO: Implement translation logic here
        # Example:
        # df[f"{{self.name}}_main"] = df['Close'].rolling(window=config.period).mean()
        
        return df
"""


def main():
    parser = argparse.ArgumentParser(description="Generate Python indicator skeleton from MQ4.")
    parser.add_argument("--mq4", type=str, help="Path to the MQ4 file.")
    parser.add_argument("--json", type=str, help="Path to pre-parsed JSON metadata.")
    parser.add_argument("--name", type=str, required=True, help="Name of the indicator class (e.g. MyIndicator)")
    parser.add_argument("--outdir", type=str, default="src/nnfx_crypto/indicators", help="Output directory")

    args = parser.parse_args()

    if not args.mq4 and not args.json:
        print("Error: Must provide either --mq4 or --json.")
        return

    metadata = {
        "parameters": [],
        "buffers": 0,
        "indicator_calls": []
    }

    if args.json:
        try:
            with open(args.json, 'r') as f:
                metadata = json.load(f)
        except Exception as e:
            print(f"Error reading JSON: {e}")
            return
    elif args.mq4:
        mq4_path = Path(args.mq4)
        if not mq4_path.exists():
            print(f"Error: File {args.mq4} not found.")
            return
        
        try:
            content = mq4_path.read_text(encoding='utf-8', errors='replace')
            metadata = parse_mq4(content)
        except Exception as e:
            print(f"Error parsing MQ4: {e}")
            return

    # Build params string
    params_lines = []
    for p in metadata.get("parameters", []):
        ptype = "float" if p["type"] == "double" else "int" if p["type"] == "int" else "str"
        default_val = p.get("default")
        if default_val:
            params_lines.append(f"    {p['name']}: {ptype} = {default_val}")
        else:
            params_lines.append(f"    {p['name']}: {ptype}")
            
    if not params_lines:
        params_lines.append("    pass  # No parameters detected")
        
    params_str = "\n".join(params_lines)
    
    class_name = args.name
    indicator_name = class_name.lower()

    code = TEMPLATE.format(
        class_name=class_name,
        indicator_name=indicator_name,
        params_str=params_str,
        buffers_count=metadata.get("buffers", 0),
        indicator_calls=", ".join(metadata.get("indicator_calls", ["None"]))
    )

    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{indicator_name}.py"
    
    if out_file.exists():
        print(f"Warning: {out_file} already exists. Refusing to overwrite.")
        return
        
    out_file.write_text(code, encoding='utf-8')
    print(f"Successfully generated skeleton at {out_file}")
    print(f"Don't forget to register it in {out_dir / 'registry.py'}")


if __name__ == "__main__":
    main()
