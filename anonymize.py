from __future__ import annotations

import os
import struct
import zlib
from dataclasses import dataclass, field

from chunktypes import TYPE_IDAT, TYPE_IEND, TYPE_IHDR, TYPE_PLTE
from parser import PNG_SIGNATURE, ChunkRecord, is_critical, parse_png

ALLOWED_CHUNKS = {TYPE_IHDR, TYPE_PLTE, TYPE_IDAT, TYPE_IEND}


@dataclass
class AnonymizeReport:
    input_path: str
    output_path: str
    removed_chunks: list[str] = field(default_factory=list)
    removed_trailing_bytes: int = 0
    idat_chunks_before: int = 0
    idat_chunks_after: int = 0

    @property
    def input_size(self) -> int:
        return os.path.getsize(self.input_path)

    @property
    def output_size(self) -> int:
        return os.path.getsize(self.output_path)


def compute_crc(chunk_type: bytes, data: bytes) -> int:
    return zlib.crc32(chunk_type + data) & 0xFFFFFFFF


def write_chunk(file, chunk_type: bytes, data: bytes) -> None:
    file.write(struct.pack(">I", len(data)))
    file.write(chunk_type)
    file.write(data)
    file.write(struct.pack(">I", compute_crc(chunk_type, data)))


def normalize_chunks(chunks: list[ChunkRecord]) -> list[tuple[bytes, bytes]]:
    """Keep only image-critical chunks in canonical order."""
    by_type: dict[bytes, list[ChunkRecord]] = {}
    for chunk in chunks:
        if chunk.type not in ALLOWED_CHUNKS:
            continue
        by_type.setdefault(chunk.type, []).append(chunk)

    if TYPE_IHDR not in by_type or len(by_type[TYPE_IHDR]) != 1:
        raise ValueError("PNG must contain exactly one IHDR chunk")
    if TYPE_IEND not in by_type or len(by_type[TYPE_IEND]) != 1:
        raise ValueError("PNG must contain exactly one IEND chunk")
    if TYPE_IDAT not in by_type:
        raise ValueError("PNG must contain at least one IDAT chunk")

    ihdr_data = by_type[TYPE_IHDR][0].data
    _, _, _, color_type, _, _, _ = struct.unpack(">IIBBBBB", ihdr_data)

    ordered: list[tuple[bytes, bytes]] = [(TYPE_IHDR, ihdr_data)]

    if color_type == 3:
        if TYPE_PLTE not in by_type:
            raise ValueError("indexed-color PNG requires a PLTE chunk")
        ordered.append((TYPE_PLTE, by_type[TYPE_PLTE][0].data))

    for idat in by_type[TYPE_IDAT]:
        ordered.append((TYPE_IDAT, idat.data))

    ordered.append((TYPE_IEND, b""))
    return ordered


def anonymize_chunks(chunks: list[ChunkRecord], trailing: bytes = b"") -> tuple[list[tuple[bytes, bytes]], list[str]]:
    """Return normalized chunks and names of removed ancillary chunks."""
    ihdr = next(chunk for chunk in chunks if chunk.type == TYPE_IHDR)
    color_type = struct.unpack(">IIBBBBB", ihdr.data)[3]

    removed: list[str] = []
    for chunk in chunks:
        name = chunk.type.decode("latin-1")
        if not is_critical(chunk.type):
            removed.append(name)
        elif chunk.type == TYPE_PLTE and color_type != 3:
            removed.append(name)

    normalized = normalize_chunks(chunks)
    return normalized, removed


def write_png(path: str, chunks: list[tuple[bytes, bytes]]) -> None:
    with open(path, "wb") as file:
        file.write(PNG_SIGNATURE)
        for chunk_type, data in chunks:
            write_chunk(file, chunk_type, data)


def anonymize_png(input_path: str, output_path: str) -> AnonymizeReport:
    result = parse_png(input_path, verify_crc=True)

    if not result.signature_ok:
        raise ValueError(f"invalid PNG signature: {input_path}")
    if result.errors:
        raise ValueError(f"cannot anonymize broken PNG: {result.errors[0]}")
    if result.ihdr is None:
        raise ValueError("missing IHDR chunk")

    idat_before = len(result.chunks_of_type(TYPE_IDAT))
    normalized, removed = anonymize_chunks(result.chunks, result.trailing)
    write_png(output_path, normalized)

    return AnonymizeReport(
        input_path=input_path,
        output_path=output_path,
        removed_chunks=removed,
        removed_trailing_bytes=len(result.trailing),
        idat_chunks_before=idat_before,
        idat_chunks_after=len([c for c in normalized if c[0] == TYPE_IDAT]),
    )
