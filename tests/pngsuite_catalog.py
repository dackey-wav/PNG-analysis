"""
http://www.schaik.com/pngsuite/pngsuite.html
"""

from __future__ import annotations

from pathlib import Path

PNG_SUITE_DIR = Path(__file__).resolve().parent.parent / "data" / "PngSuite-2017jul19"

COLOR_CODE_TO_TYPE = {
    "0g": 0,
    "2c": 2,
    "3p": 3,
    "4a": 4,
    "6a": 6,
}

CATEGORY_ORDER = (
    "corrupted_files",
    "ancillary_chunks",
    "chunk_order",
    "zlib_compression",
    "image_filtering",
    "gamma_values",
    "background_colors",
    "transparency",
    "additional_palettes",
    "odd_sizes",
    "interlacing",
    "basic_formats",
    "meta",
)

ANCILLARY_PREFIXES = (
    "exif",
    "cm0",
    "cm7",
    "cm9",
    "cs3",
    "cs5",
    "cs8",
    "cdf",
    "cdh",
    "cds",
    "cdu",
    "ccw",
    "ch1",
    "ch2",
    "ct0",
    "ct1",
    "ctz",
    "cte",
    "ctf",
    "ctg",
    "cth",
    "ctj",
)


def categorize_png(filename: str) -> str:
    name = filename.lower()

    if name == "pngsuite.png":
        return "meta"
    if name.startswith("x") or name.startswith("f99"):
        return "corrupted_files"
    if any(name.startswith(prefix) for prefix in ANCILLARY_PREFIXES):
        return "ancillary_chunks"
    if name.startswith(("oi1", "oi2", "oi4", "oi9")):
        return "chunk_order"
    if name.startswith(("z00", "z03", "z06", "z09")):
        return "zlib_compression"
    if name.startswith(("f00", "f01", "f02", "f03", "f04")):
        return "image_filtering"
    if name.startswith(("g03", "g04", "g05", "g07", "g10", "g25")):
        return "gamma_values"
    if name.startswith("bg"):
        return "background_colors"
    if name.startswith(("tb", "tp", "tm3")):
        return "transparency"
    if name.startswith(("ps", "pp")):
        return "additional_palettes"
    if any(name.startswith(f"s{i:02d}") for i in range(32, 41)):
        return "additional_palettes"
    if any(name.startswith(f"s{i:02d}") for i in range(1, 10)):
        return "odd_sizes"
    if name.startswith("basi"):
        return "interlacing"
    if name.startswith("basn"):
        return "basic_formats"
    return "uncategorized"


def decode_standard_filename(filename: str) -> dict:
    """Decode the color/interlace/bit-depth suffix used by most PngSuite files."""
    stem = Path(filename).stem.lower()
    info = {
        "stem": stem,
        "interlaced": None,
        "color_code": None,
        "color_type": None,
        "bit_depth": None,
    }

    if stem.startswith(("basn", "basi")):
        info["interlaced"] = stem.startswith("basi")
        info["color_code"] = stem[4:6]
        info["bit_depth"] = int(stem[6:8])
    elif len(stem) >= 8 and stem[4] in ("i", "n"):
        info["interlaced"] = stem[4] == "i"
        info["color_code"] = stem[5:7]
        info["bit_depth"] = int(stem[7:9])

    if info["color_code"] in COLOR_CODE_TO_TYPE:
        info["color_type"] = COLOR_CODE_TO_TYPE[info["color_code"]]

    return info


def expected_odd_size(filename: str) -> tuple[int, int] | None:
    stem = Path(filename).stem.lower()
    if stem[1:3].isdigit() and stem.startswith("s"):
        size = int(stem[1:3])
        if 1 <= size <= 9 or 32 <= size <= 40:
            return size, size
    return None


def expected_idat_count(filename: str) -> int | None:
    stem = Path(filename).stem.lower()
    if stem.startswith("oi1"):
        return 1
    if stem.startswith("oi2"):
        return 2
    if stem.startswith("oi4"):
        return 4
    if stem.startswith("oi9"):
        return None  # many single-byte chunks; checked separately
    return None


def corrupted_expectations(filename: str) -> dict:
    stem = Path(filename).stem.lower()
    prefix = stem[:3]

    expectations: dict = {"should_be_invalid": True}

    if stem.startswith("xs"):
        expectations["signature_ok"] = False
    elif prefix == "xhd" or prefix == "xlf":
        if prefix == "xhd":
            expectations["bad_crc_chunk"] = "IHDR"
        else:
            expectations["signature_ok"] = False
    elif prefix == "xcs":
        expectations["bad_crc_chunk"] = "IDAT"
    elif prefix == "xdt":
        expectations["missing_chunk"] = b"IDAT"
    elif prefix == "xc1":
        expectations["ihdr_color_type"] = 1
    elif prefix == "xc9":
        expectations["ihdr_color_type"] = 9
    elif prefix == "xd0":
        expectations["ihdr_bit_depth"] = 0
    elif prefix == "xd3":
        expectations["ihdr_bit_depth"] = 3
    elif prefix == "xd9":
        expectations["ihdr_bit_depth"] = 99
    elif stem.startswith("f99"):
        expectations["signature_ok"] = True
        expectations["valid_crc"] = True

    return expectations


def build_catalog(png_dir: Path = PNG_SUITE_DIR) -> dict[str, list[Path]]:
    catalog = {category: [] for category in CATEGORY_ORDER}
    catalog["uncategorized"] = []

    for path in sorted(png_dir.glob("*.png")):
        category = categorize_png(path.name)
        catalog.setdefault(category, []).append(path)

    return catalog


def files_for_category(category: str, png_dir: Path = PNG_SUITE_DIR) -> list[Path]:
    return build_catalog(png_dir)[category]
