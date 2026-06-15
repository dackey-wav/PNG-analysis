import argparse
import sys

from anonymize import anonymize_png
from chunktypes import TYPE_IDAT, TYPE_IEND, TYPE_PLTE
from chunks.IDAT import format_idat_summary
from chunks.IEND import ChunkIEND
from chunks.PLTE import ChunkPLTE
from chunks.ancillary import parse_ancillary
from console import (
    fail,
    field_line,
    format_chunk_row,
    heading,
    label,
    metric_name,
    ok,
    section,
    warn,
)
from parser import is_critical, parse_png


def inspect_png(path: str) -> None:
    result = parse_png(path)

    status = ok("PNG is OK") if result.signature_ok else fail("Invalid PNG signature")
    print(status)
    print(field_line("File", f"{result.file_size} bytes"))
    print()

    print(section("Chunks"))
    for chunk in result.chunks:
        critical = is_critical(chunk.type)
        role = "critical" if critical else "ancillary"
        print(
            format_chunk_row(
                chunk.offset,
                chunk.type.decode("latin-1"),
                len(chunk.data),
                role,
                critical=critical,
                crc_ok_flag=chunk.crc_ok,
            )
        )
    print()

    if result.ihdr is None:
        print(fail("IHDR: not found"))
        return

    print(section("IHDR"))
    print(result.ihdr)

    if result.ihdr.use_pallete():
        plte_chunks = result.chunks_of_type(TYPE_PLTE)
        if not plte_chunks:
            print(warn("WARNING: indexed-color image but no PLTE chunk found"))
        else:
            print()
            print(section("PLTE"))
            plte = plte_chunks[0]
            print(ChunkPLTE(plte.type, plte.data, plte.crc))

    ancillary_chunks = [
        chunk for chunk in result.chunks if not is_critical(chunk.type)
    ]
    if ancillary_chunks:
        print()
        print(section("Ancillary chunks"))
        for chunk in ancillary_chunks:
            name = chunk.type.decode("latin-1")
            print(f"  {label(f'[{name} @ 0x{chunk.offset:04X}]')}")
            parsed = parse_ancillary(chunk.type, chunk.data, chunk.crc)
            for line in str(parsed).splitlines():
                print(f"  {line}")
            print()

    print(section("IDAT"))
    idat_chunks = [
        (chunk.type, chunk.data, chunk.crc)
        for chunk in result.chunks_of_type(TYPE_IDAT)
    ]
    print(format_idat_summary(idat_chunks))
    print()

    print(section("IEND"))
    iend = result.chunks_of_type(TYPE_IEND)[0]
    print(ChunkIEND(iend.type, iend.data, iend.crc))

    if result.trailing:
        print()
        print(warn(f"WARNING: {len(result.trailing)} bytes after IEND"))
        print(f"  {metric_name(result.trailing[:64].hex())}")

    if result.ihdr.bit_depth_warning:
        print()
        print(warn("WARNING: bit depth is not allowed for this color type"))


def run_anonymize(input_path: str, output_path: str) -> None:
    report = anonymize_png(input_path, output_path)

    print(heading("Anonymized PNG"))
    print(field_line("Input", report.input_path))
    print(field_line("Output", report.output_path))
    print(
        field_line(
            "Size",
            f"{report.input_size} -> {report.output_size} bytes",
        )
    )

    if report.removed_chunks:
        removed = ", ".join(report.removed_chunks)
        print(field_line("Removed chunks", removed))
    else:
        print(field_line("Removed chunks", "(none)"))

    if report.removed_trailing_bytes:
        print(
            field_line(
                "Trailing bytes removed",
                str(report.removed_trailing_bytes),
            )
        )

    print(
        field_line(
            "IDAT chunks",
            f"{report.idat_chunks_before} -> {report.idat_chunks_after}",
        )
    )
    print(ok("Image data unchanged"))


def main() -> None:
    if (
        len(sys.argv) > 1
        and sys.argv[1] not in ("inspect", "anonymize")
        and not sys.argv[1].startswith("-")
    ):
        sys.argv.insert(1, "inspect")

    parser = argparse.ArgumentParser(description="Inspect or anonymize PNG files.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Show PNG chunk metadata")
    inspect_parser.add_argument("path", nargs="?", default="data/parrot.png")

    anonymize_parser = subparsers.add_parser(
        "anonymize", help="Remove ancillary metadata from a PNG"
    )
    anonymize_parser.add_argument("input", help="Input PNG path")
    anonymize_parser.add_argument("output", help="Output PNG path")

    args = parser.parse_args()

    if args.command == "inspect":
        inspect_png(args.path)
    elif args.command == "anonymize":
        run_anonymize(args.input, args.output)


if __name__ == "__main__":
    main()
