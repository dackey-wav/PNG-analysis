from __future__ import annotations

import pytest

from chunktypes import (
    TYPE_IDAT,
    TYPE_PLTE,
    TYPE_bKGD,
    TYPE_eXIf,
    TYPE_gAMA,
    TYPE_iTXt,
    TYPE_pHYs,
    TYPE_sPLT,
    TYPE_tEXt,
    TYPE_tIME,
    TYPE_tRNS,
    TYPE_zTXt,
)
from chunks.ancillary import ChunkExif, parse_ancillary
from parser import parse_png, parse_png_lenient
from tests.pngsuite_catalog import (
    CATEGORY_ORDER,
    build_catalog,
    corrupted_expectations,
    decode_standard_filename,
    expected_idat_count,
    expected_odd_size,
    files_for_category,
)

PNG_SUITE = files_for_category("basic_formats")[0].parent


def _all_crc_ok(result) -> bool:
    return all(chunk.crc_ok for chunk in result.chunks)


@pytest.fixture(scope="session")
def catalog():
    return build_catalog(PNG_SUITE)


@pytest.fixture(scope="session")
def all_pngsuite_files(catalog):
    files = []
    for category in CATEGORY_ORDER:
        files.extend(catalog.get(category, []))
    files.extend(catalog.get("uncategorized", []))
    return files


class TestCatalog:
    def test_all_pngsuite_files_are_categorized(self, catalog):
        assert catalog["uncategorized"] == []
        total = sum(len(files) for files in catalog.values())
        assert total == len(list(PNG_SUITE.glob("*.png")))


@pytest.mark.parametrize(
    "path",
    files_for_category("basic_formats"),
    ids=lambda p: p.name,
)
def test_basic_formats(path):
    result = parse_png(str(path))

    assert result.signature_ok
    assert _all_crc_ok(result)
    assert result.ihdr is not None
    assert result.ihdr.interlacem == 0

    info = decode_standard_filename(path.name)
    assert info["color_type"] == result.ihdr.colort
    assert info["bit_depth"] == result.ihdr.bitd


@pytest.mark.parametrize(
    "path",
    files_for_category("interlacing"),
    ids=lambda p: p.name,
)
def test_interlacing(path):
    result = parse_png(str(path))

    assert result.signature_ok
    assert result.ihdr is not None
    assert result.ihdr.interlacem == 1

    info = decode_standard_filename(path.name)
    assert info["interlaced"] is True


@pytest.mark.parametrize(
    "path",
    files_for_category("odd_sizes"),
    ids=lambda p: p.name,
)
def test_odd_sizes(path):
    result = parse_png(str(path))

    assert result.signature_ok
    assert result.ihdr is not None

    expected = expected_odd_size(path.name)
    assert expected is not None
    assert (result.ihdr.width, result.ihdr.height) == expected


@pytest.mark.parametrize(
    "path",
    files_for_category("background_colors"),
    ids=lambda p: p.name,
)
def test_background_colors(path):
    result = parse_png(str(path))

    assert result.signature_ok
    assert result.ihdr is not None
    assert result.ihdr.colort in (4, 6)

    name = path.name.lower()
    if name.startswith("bga"):
        # alpha channel without a suggested background color
        assert not result.has_chunk(TYPE_bKGD)
    else:
        assert result.has_chunk(TYPE_bKGD)


@pytest.mark.parametrize(
    "path",
    files_for_category("transparency"),
    ids=lambda p: p.name,
)
def test_transparency(path):
    result = parse_png(str(path))

    assert result.signature_ok
    assert result.ihdr is not None

    if path.name.lower().startswith("tp0"):
        assert not result.has_chunk(TYPE_tRNS)
    else:
        assert result.has_chunk(TYPE_tRNS)


@pytest.mark.parametrize(
    "path",
    files_for_category("gamma_values"),
    ids=lambda p: p.name,
)
def test_gamma_values(path):
    result = parse_png(str(path))

    assert result.signature_ok
    assert result.has_chunk(TYPE_gAMA)


@pytest.mark.parametrize(
    "path",
    files_for_category("image_filtering"),
    ids=lambda p: p.name,
)
def test_image_filtering(path):
    result = parse_png(str(path))

    assert result.signature_ok
    assert result.has_chunk(TYPE_IDAT)


@pytest.mark.parametrize(
    "path",
    files_for_category("additional_palettes"),
    ids=lambda p: p.name,
)
def test_additional_palettes(path):
    result = parse_png(str(path))

    assert result.signature_ok

    name = path.name.lower()
    if name.startswith("ps"):
        assert result.has_chunk(TYPE_sPLT)
    elif name.startswith("pp"):
        assert result.has_chunk(TYPE_PLTE)
    else:
        assert result.has_chunk(TYPE_PLTE)


@pytest.mark.parametrize(
    "path",
    files_for_category("chunk_order"),
    ids=lambda p: p.name,
)
def test_chunk_order(path):
    result = parse_png(str(path))

    assert result.signature_ok
    idat_count = len(result.chunks_of_type(TYPE_IDAT))
    expected = expected_idat_count(path.name)

    if path.name.lower().startswith("oi9"):
        assert idat_count > 1
        assert all(len(chunk.data) == 1 for chunk in result.chunks_of_type(TYPE_IDAT))
    else:
        assert idat_count == expected


@pytest.mark.parametrize(
    "path",
    files_for_category("zlib_compression"),
    ids=lambda p: p.name,
)
def test_zlib_compression(path):
    result = parse_png(str(path))

    assert result.signature_ok
    idat = result.chunks_of_type(TYPE_IDAT)[0].data
    assert idat[0] == 0x78


@pytest.mark.parametrize(
    "path",
    files_for_category("ancillary_chunks"),
    ids=lambda p: p.name,
)
def test_ancillary_chunks(path):
    result = parse_png(str(path))
    assert result.signature_ok

    name = path.name.lower()
    ancillary_types = {
        chunk.type
        for chunk in result.chunks
        if chunk.type.decode("latin-1")[0].islower()
    }

    if name.startswith("exif"):
        assert TYPE_eXIf in ancillary_types
        parsed = parse_ancillary(TYPE_eXIf, result.chunks_of_type(TYPE_eXIf)[0].data, 0)
        assert isinstance(parsed, ChunkExif)
    elif name.startswith(("cm0", "cm7", "cm9")):
        assert TYPE_tIME in ancillary_types
    elif name.startswith(("ct1", "cte", "ctf", "ctg", "cth", "ctj")):
        assert TYPE_tEXt in ancillary_types or TYPE_iTXt in ancillary_types
    elif name.startswith("ctz"):
        assert TYPE_zTXt in ancillary_types
    elif name.startswith(("cdf", "cdh", "cds", "cdu")):
        assert TYPE_pHYs in ancillary_types
    elif name.startswith("ccw"):
        assert b"cHRM" in ancillary_types
    elif name.startswith(("ch1", "ch2")):
        assert b"hIST" in ancillary_types
    elif name.startswith(("cs3", "cs5")):
        assert b"sBIT" in ancillary_types
    elif name.startswith("cs8"):
        assert result.has_chunk(TYPE_IDAT)

    for chunk in result.chunks:
        if chunk.type.decode("latin-1")[0].islower():
            parsed = parse_ancillary(chunk.type, chunk.data, chunk.crc)
            assert parsed is not None
            assert str(parsed)


@pytest.mark.parametrize(
    "path",
    files_for_category("corrupted_files"),
    ids=lambda p: p.name,
)
def test_corrupted_files(path):
    expectations = corrupted_expectations(path.name)
    result = parse_png_lenient(str(path))

    if expectations.get("signature_ok") is False:
        assert not result.signature_ok
    elif expectations.get("signature_ok") is True:
        assert result.signature_ok

    if "bad_crc_chunk" in expectations:
        assert any(
            error.startswith(f"chunk_checksum_failed:{expectations['bad_crc_chunk']}")
            for error in result.errors
        )

    if "missing_chunk" in expectations:
        assert not result.has_chunk(expectations["missing_chunk"])

    if "ihdr_color_type" in expectations and result.ihdr is not None:
        assert result.ihdr.colort == expectations["ihdr_color_type"]

    if "ihdr_bit_depth" in expectations and result.ihdr is not None:
        assert result.ihdr.bitd == expectations["ihdr_bit_depth"]

    if expectations.get("valid_crc"):
        assert _all_crc_ok(result)


def test_pngsuite_contains_exif_sample(catalog):
    exif_files = [path for path in catalog["ancillary_chunks"] if path.name.startswith("exif")]
    assert exif_files
    result = parse_png(str(exif_files[0]))
    assert result.has_chunk(TYPE_eXIf)
