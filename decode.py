import argparse

from chunktypes import TYPE_IDAT, TYPE_IEND, TYPE_IHDR, TYPE_PLTE
from chunks.IDAT import format_idat_summary
from chunks.IEND import ChunkIEND
from chunks.IHDR import ChunkIHDR
from chunks.PLTE import ChunkPLTE
from chunks.ancillary import parse_ancillary
from parser import is_critical, parse_png


def inspect_png(path: str) -> None:
    result = parse_png(path)

    print("PNG is OK" if result.signature_ok else "Invalid PNG signature")
    print(f"File size: {result.file_size} bytes\n")

    print("Chunks:")
    for chunk in result.chunks:
        critical = "critical" if is_critical(chunk.type) else "ancillary"
        crc_status = "OK" if chunk.crc_ok else "FAIL"
        print(
            f"  0x{chunk.offset:04X}  {chunk.type.decode('latin-1'):4s}  "
            f"len={len(chunk.data):5d}  {critical:9s}  crc={crc_status}"
        )
    print()

    if result.ihdr is None:
        print("IHDR: not found")
        return

    print("IHDR:")
    print(result.ihdr)

    if result.ihdr.use_pallete():
        plte_chunks = result.chunks_of_type(TYPE_PLTE)
        if not plte_chunks:
            print("WARNING: indexed-color image but no PLTE chunk found")
        else:
            plte = plte_chunks[0]
            print(ChunkPLTE(plte.type, plte.data, plte.crc))
            print()

    ancillary_chunks = [
        chunk for chunk in result.chunks if not is_critical(chunk.type)
    ]
    if ancillary_chunks:
        print("Ancillary chunks:")
        for chunk in ancillary_chunks:
            name = chunk.type.decode("latin-1")
            print(f"  [{name} @ 0x{chunk.offset:04X}]")
            print(f"  {parse_ancillary(chunk.type, chunk.data, chunk.crc)}")
            print()

    idat_chunks = [(chunk.type, chunk.data, chunk.crc) for chunk in result.chunks_of_type(TYPE_IDAT)]
    print(format_idat_summary(idat_chunks))
    print()

    iend = result.chunks_of_type(TYPE_IEND)[0]
    print(ChunkIEND(iend.type, iend.data, iend.crc))

    if result.trailing:
        print(f"\nWARNING: {len(result.trailing)} bytes after IEND")
        print(result.trailing[:64].hex())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect PNG chunks and metadata.")
    parser.add_argument("path", nargs="?", default="data/parrot.png")
    args = parser.parse_args()
    inspect_png(args.path)
