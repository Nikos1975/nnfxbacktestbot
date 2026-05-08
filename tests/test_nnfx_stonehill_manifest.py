import json
from pathlib import Path

from nnfx_crypto.tools.stonehill_manifest import build_manifest, write_manifest


def test_build_manifest_records_download_hashes(tmp_path: Path):
    downloads = tmp_path / "downloads"
    extracted = tmp_path / "extracted"
    downloads.mkdir()
    extracted.mkdir()
    (downloads / "Example.zip").write_bytes(b"abc")
    (extracted / "Example.mq4").write_text("input int Period = 10;", encoding="utf-8")

    manifest = build_manifest(downloads, extracted, source_url="https://example.com/library")

    assert manifest["source_url"] == "https://example.com/library"
    assert manifest["downloads"][0]["name"] == "Example.zip"
    assert manifest["downloads"][0]["sha256"] == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert manifest["extracted_files"][0]["extension"] == ".mq4"


def test_write_manifest_outputs_json(tmp_path: Path):
    downloads = tmp_path / "downloads"
    extracted = tmp_path / "extracted"
    output = tmp_path / "manifest.json"
    downloads.mkdir()
    extracted.mkdir()
    (downloads / "Example.zip").write_bytes(b"abc")

    write_manifest(downloads, extracted, output, source_url="https://example.com/library")

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["downloads"][0]["name"] == "Example.zip"
