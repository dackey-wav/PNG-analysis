import argparse
import os
import struct
import zlib

from chunktypes import TYPE_IDAT, TYPE_IEND, TYPE_IHDR, TYPE_PLTE
from chunks.IDAT import format_idat_summary
from chunks.IEND import ChunkIEND
from chunks.IHDR import ChunkIHDR
from chunks.PLTE import ChunkPLTE

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def is_critical(chunk_type: bytes) -> bool:
    return chr(chunk_type[0]).isupper()


def read_chunk(f):
    """Returns (chunk_type, chunk_data, crc) or None at EOF."""
    header = f.read(8)
    if not header:
        return None

    chunk_length, chunk_type = struct.unpack(">I4s", header)
    chunk_data = f.read(chunk_length)
    chunk_crc, = struct.unpack(">I", f.read(4))
    checksum = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF

    if chunk_crc != checksum:
        raise Exception(
            f"chunk checksum failed for {chunk_type!r}: {chunk_crc} != {checksum}"
        )

    return chunk_type, chunk_data, checksum


def inspect_png(path: str) -> None:
    file_size = os.path.getsize(path)

    with open(path, "rb") as file:
        if file.read(len(PNG_SIGNATURE)) != PNG_SIGNATURE:
            raise Exception("Invalid PNG Signature")

        print("PNG is OK")
        print(f"File size: {file_size} bytes\n")

        chunks = []
        offset = len(PNG_SIGNATURE)

        while True:
            result = read_chunk(file)
            if result is None:
                raise Exception("Unexpected end of file before IEND")

            chunk_type, chunk_data, checksum = result
            chunks.append((offset, chunk_type, chunk_data, checksum))
            offset += 8 + len(chunk_data) + 4

            if chunk_type == TYPE_IEND:
                break

        trailing = file.read()

    print("Chunks:")
    for chunk_offset, chunk_type, chunk_data, checksum in chunks:
        critical = "critical" if is_critical(chunk_type) else "ancillary"
        print(
            f"  0x{chunk_offset:04X}  {chunk_type.decode('latin-1'):4s}  "
            f"len={len(chunk_data):5d}  {critical:9s}  crc=OK"
        )
    print()

    ihdr_chunk = next(c for c in chunks if c[1] == TYPE_IHDR)
    _, ihdr_data, ihdr_crc = ihdr_chunk[1:]
    ihdr = ChunkIHDR(TYPE_IHDR, ihdr_data, ihdr_crc)
    print("IHDR:")
    print(ihdr)

    if ihdr.use_pallete():
        plte_chunk = next((c for c in chunks if c[1] == TYPE_PLTE), None)
        if plte_chunk is None:
            print("WARNING: indexed-color image but no PLTE chunk found")
        else:
            _, plte_data, plte_crc = plte_chunk[1:]
            print(ChunkPLTE(TYPE_PLTE, plte_data, plte_crc))
            print()

    idat_chunks = [(t, d, c) for _, t, d, c in chunks if t == TYPE_IDAT]
    print(format_idat_summary(idat_chunks))
    print()

    iend_chunk = next(c for c in chunks if c[1] == TYPE_IEND)
    _, iend_data, iend_crc = iend_chunk[1:]
    print(ChunkIEND(TYPE_IEND, iend_data, iend_crc))

    if trailing:
        print(f"\nWARNING: {len(trailing)} bytes after IEND")
        print(trailing[:64].hex())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect PNG critical chunks.")
    parser.add_argument("path", nargs="?", default="data/parrot.png")
    args = parser.parse_args()
    inspect_png(args.path)
