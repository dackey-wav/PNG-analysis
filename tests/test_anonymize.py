from __future__ import annotations

import struct
from pathlib import Path

import pytest

from anonymize import anonymize_png
from chunktypes import TYPE_PLTE
from parser import PNG_SIGNATURE, parse_png

PNG_SUITE = Path(__file__).resolve().parent.parent / "data" / "PngSuite-2017jul19"


def _idat_bytes(path: str) -> bytes:
    result = parse_png(path)
    return b"".join(chunk.data for chunk in result.chunks_of_type(b"IDAT"))


def _ancillary_names(path: str) -> list[str]:
    result = parse_png(path)
    return [
        chunk.type.decode("latin-1")
        for chunk in result.chunks
        if chunk.type.decode("latin-1")[0].islower()
    ]


def test_anonymize_removes_ancillary_from_grayscale(tmp_path):
    src = "data/grayscale.png"
    out = tmp_path / "clean.png"

    assert _ancillary_names(src)

    report = anonymize_png(src, str(out))

    assert out.exists()
    assert report.removed_chunks
    assert _ancillary_names(str(out)) == []


def test_anonymize_removes_exif(tmp_path):
    src = str(PNG_SUITE / "exif2c08.png")
    out = tmp_path / "clean.png"

    report = anonymize_png(src, str(out))

    result = parse_png(str(out))
    assert b"eXIf" not in result.chunk_types
    assert "eXIf" in report.removed_chunks


def test_anonymize_preserves_idat_payload(tmp_path):
    src = "data/screenshot_desktop.png"
    out = tmp_path / "clean.png"

    anonymize_png(src, str(out))

    assert _idat_bytes(src) == _idat_bytes(str(out))


def test_anonymize_keeps_plte_for_indexed_color(tmp_path):
    src = "data/parrot.png"
    out = tmp_path / "clean.png"

    anonymize_png(src, str(out))

    result = parse_png(str(out))
    assert result.has_chunk(TYPE_PLTE)
    assert result.ihdr is not None
    assert result.ihdr.colort == 3


def test_anonymize_normalizes_chunk_order(tmp_path):
    src = "data/grayscale.png"
    out = tmp_path / "clean.png"

    anonymize_png(src, str(out))

    result = parse_png(str(out))
    names = result.chunk_type_names
    assert names[0] == "IHDR"
    assert names[-1] == "IEND"
    assert "IDAT" in names
    assert all(name not in names for name in ("gAMA", "tEXt", "tIME", "bKGD", "cHRM"))


def test_anonymize_strips_trailing_bytes(tmp_path):
    src = tmp_path / "with_trailing.png"
    out = tmp_path / "clean.png"

    original = parse_png("data/wierd.png")
    with open(src, "wb") as file:
        file.write(PNG_SIGNATURE)
        for chunk in original.chunks:
            file.write(struct.pack(">I", len(chunk.data)))
            file.write(chunk.type)
            file.write(chunk.data)
            file.write(struct.pack(">I", chunk.crc))
        file.write(b"SECRET_TRAILING_DATA")

    report = anonymize_png(str(src), str(out))

    assert report.removed_trailing_bytes == len(b"SECRET_TRAILING_DATA")
    cleaned = parse_png(str(out))
    assert cleaned.trailing == b""


def test_anonymize_output_has_valid_crc(tmp_path):
    src = str(PNG_SUITE / "ct1n0g04.png")
    out = tmp_path / "clean.png"

    anonymize_png(src, str(out))

    result = parse_png(str(out), verify_crc=True)
    assert result.errors == []


def test_anonymize_smaller_for_metadata_rich_files(tmp_path):
    src = "data/grayscale.png"
    out = tmp_path / "clean.png"

    report = anonymize_png(src, str(out))

    assert report.output_size < report.input_size
