from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path


STRATEGIES = [
    "NnfxCoreJmaTdfiKijunVoxiChandelier",
    "NnfxAdaptiveOttHalftrendRsxKeltnerVolStop",
    "NnfxVolumeMcginleyAlphatrendStcChopWae",
    "NnfxAlphaTrendRsxVoxiChandelier",
    "NnfxTdfiKijunChopChandelier",
    "NnfxMacZVwapOttVoxiVolStop",
    "NnfxPriceOnlySmiMfiKeltnerChandelier",
]


def replace_class_name(source: str, old: str, new: str) -> str:
    return re.sub(rf"\bclass\s+{re.escape(old)}\b", f"class {new}", source, count=1)


def replace_minimal_roi(source: str) -> str:
    tree = ast.parse(source)
    class_node = next((n for n in tree.body if isinstance(n, ast.ClassDef)), None)
    if class_node is None:
        raise ValueError("No class definition found.")

    roi_assign = None
    for node in class_node.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "minimal_roi":
                    roi_assign = node
                    break
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and target.id == "minimal_roi":
                roi_assign = node
        if roi_assign:
            break

    replacement = "    minimal_roi = {\"0\": 100}\n"

    if roi_assign is None:
        insert_line = class_node.body[0].lineno if class_node.body else class_node.lineno + 1
        lines = source.splitlines(keepends=True)
        lines.insert(insert_line, replacement)
        return "".join(lines)

    start = roi_assign.lineno - 1
    end = getattr(roi_assign, "end_lineno", roi_assign.lineno)

    lines = source.splitlines(keepends=True)
    lines[start:end] = [replacement]
    return "".join(lines)


def ensure_exit_signal(source: str) -> str:
    # If the strategy explicitly disables exit signals, turn them on.
    source = re.sub(r"^(\s*)use_exit_signal\s*=\s*False\s*$", r"\1use_exit_signal = True", source, flags=re.MULTILINE)
    return source


def make_signal_only_strategy(source_path: Path, dest_path: Path, old_class: str, new_class: str) -> None:
    source = source_path.read_text(encoding="utf-8")
    source = replace_class_name(source, old_class, new_class)
    source = replace_minimal_roi(source)
    source = ensure_exit_signal(source)

    header = (
        "# Auto-generated signal-exit-only variant.\n"
        "# Purpose: remove Freqtrade ROI-table exits to test indicator exit logic.\n"
        "# Mechanical change: minimal_roi = {\"0\": 100}\n\n"
    )
    dest_path.write_text(header + source, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strategies-dir",
        default="user_data/strategies",
        help="Freqtrade strategies directory.",
    )
    args = parser.parse_args()

    strategies_dir = Path(args.strategies_dir)

    created = []
    missing = []

    for strategy in STRATEGIES:
        src = strategies_dir / f"{strategy}.py"
        if not src.exists():
            missing.append(str(src))
            continue

        new_strategy = f"{strategy}SignalExitOnly"
        dest = strategies_dir / f"{new_strategy}.py"

        make_signal_only_strategy(src, dest, strategy, new_strategy)
        created.append(str(dest))

    print("")
    print("Created signal-exit-only strategies:")
    for path in created:
        print(f"- {path}")

    if missing:
        print("")
        print("Missing source strategy files:")
        for path in missing:
            print(f"- {path}")

    print("")
    print("Next command:")
    print("docker compose run --rm freqtrade list-strategies")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
