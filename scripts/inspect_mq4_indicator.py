import argparse
import json
import re
from pathlib import Path


def parse_mq4(content: str) -> dict:
    """Extracts useful metadata from MQ4 content without decompiling."""
    metadata = {
        "parameters": [],
        "buffers": 0,
        "indicator_calls": [],
        "warnings": [],
        "sections": []
    }

    # Find input/extern parameters
    # Matches: extern double my_var = 1.0; or input int my_var = 1;
    param_pattern = re.compile(r'(?:extern|input)\s+([a-zA-Z0-9_]+)\s+([a-zA-Z0-9_]+)\s*(?:=\s*([^;]+))?;')
    for match in param_pattern.finditer(content):
        vtype, vname, vval = match.groups()
        metadata["parameters"].append({
            "type": vtype,
            "name": vname,
            "default": vval.strip() if vval else None
        })

    # Find buffer count
    buffer_prop_pattern = re.compile(r'#property\s+indicator_buffers\s+(\d+)')
    match = buffer_prop_pattern.search(content)
    if match:
        metadata["buffers"] = int(match.group(1))

    # Find SetIndexBuffer
    if 'SetIndexBuffer' in content:
        metadata["sections"].append("Uses SetIndexBuffer")

    # Obvious sections
    if 'int start()' in content or 'void OnCalculate(' in content or 'int OnCalculate(' in content:
        metadata["sections"].append("Has OnCalculate/start logic")

    # Find common indicator calls
    builtin_indicators = ['iMA', 'iATR', 'iRSI', 'iMACD', 'iBands', 'iStochastic', 'iCustom', 'iWPR', 'iCCI']
    for ind in builtin_indicators:
        if ind in content:
            metadata["indicator_calls"].append(ind)

    # Check for EX4 or binary signs
    if b'\x00' in content.encode('utf-8', errors='ignore') and "MZ" in content[:10]:
         metadata["warnings"].append("File appears to be a compiled binary. Decompilation is not supported.")

    return metadata


def main():
    parser = argparse.ArgumentParser(description="Parse MQ4 source file to extract parameters and structure.")
    parser.add_argument("--file", type=str, required=True, help="Path to the MQ4 file.")
    parser.add_argument("--outdir", type=str, default="research/indicators/translation_notes", help="Output directory for notes.")
    
    args = parser.parse_args()
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"Error: File {args.file} not found.")
        return

    # Attempt to read as text
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Check EX4
    if file_path.suffix.lower() == '.ex4':
        print("Error: EX4 decompilation is not supported. Please provide an MQ4 source file.")
        return

    metadata = parse_mq4(content)

    # Output to translation_notes
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{file_path.stem}_notes.json"
    
    out_file.write_text(json.dumps(metadata, indent=4))
    print(f"Translation notes written to {out_file}")


if __name__ == "__main__":
    main()
