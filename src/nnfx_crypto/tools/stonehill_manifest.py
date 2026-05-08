from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path


def build_manifest(downloads_dir: str | Path, extracted_dir: str | Path, source_url: str) -> dict:
    downloads_path = Path(downloads_dir)
    extracted_path = Path(extracted_dir)
    downloads = [_file_entry(path, downloads_path) for path in sorted(downloads_path.glob("*")) if path.is_file()]
    extracted = [
        _file_entry(path, extracted_path)
        for path in sorted(extracted_path.rglob("*"))
        if path.is_file() and "__MACOSX" not in path.parts
    ]
    return {
        "generated_on": date.today().isoformat(),
        "source_url": source_url,
        "downloads_dir": downloads_path.as_posix(),
        "extracted_dir": extracted_path.as_posix(),
        "downloads": downloads,
        "extracted_files": extracted,
    }


def write_manifest(
    downloads_dir: str | Path,
    extracted_dir: str | Path,
    output_path: str | Path,
    source_url: str,
) -> None:
    manifest = build_manifest(downloads_dir, extracted_dir, source_url)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write manifest for Stonehill indicator downloads.")
    parser.add_argument("--downloads-dir", required=True)
    parser.add_argument("--extracted-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-url", default="https://stonehillforex.com/indicator-library/")
    args = parser.parse_args()
    write_manifest(args.downloads_dir, args.extracted_dir, args.output, args.source_url)
    print(args.output)


def _file_entry(path: Path, root: Path) -> dict:
    return {
        "name": path.name,
        "relative_path": path.relative_to(root).as_posix(),
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
