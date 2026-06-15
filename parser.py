"""Low-level PNG parsing used by the inspector and tests."""

from __future__ import annotations

import os
import struct
import zlib
from dataclasses import dataclass, field

from chunktypes import TYPE_IEND, TYPE_IHDR
from chunks.IHDR import ChunkIHDR

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass
class ChunkRecord:
    offset: int
    type: bytes
    data: bytes
    crc: int
    crc_ok: bool


@dataclass
class ParseResult:
    path: str
    file_size: int
    signature_ok: bool
    chunks: list[ChunkRecord] = field(default_factory=list)
    trailing: bytes = b""
    ihdr: ChunkIHDR | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def chunk_types(self) -> list[bytes]:
        return [chunk.type for chunk in self.chunks]

    @property
    def chunk_type_names(self) -> list[str]:
        return [chunk.type.decode("latin-1") for chunk in self.chunks]

    def chunks_of_type(self, chunk_type: bytes) -> list[ChunkRecord]:
        return [chunk for chunk in self.chunks if chunk.type == chunk_type]

    def has_chunk(self, chunk_type: bytes) -> bool:
        return any(chunk.type == chunk_type for chunk in self.chunks)


def is_critical(chunk_type: bytes) -> bool:
    return chr(chunk_type[0]).isupper()


def read_chunk(f, verify_crc: bool = True) -> ChunkRecord | None:
    """Read one chunk from an open binary file positioned at chunk start."""
    header = f.read(8)
    if not header:
        return None
    if len(header) < 8:
        raise ValueError("truncated chunk header")

    chunk_length, chunk_type = struct.unpack(">I4s", header)
    chunk_data = f.read(chunk_length)
    if len(chunk_data) < chunk_length:
        raise ValueError(f"truncated chunk data for {chunk_type!r}")

    crc_bytes = f.read(4)
    if len(crc_bytes) < 4:
        raise ValueError(f"truncated CRC for {chunk_type!r}")

    chunk_crc, = struct.unpack(">I", crc_bytes)
    checksum = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
    crc_ok = chunk_crc == checksum

    if verify_crc and not crc_ok:
        raise ValueError(
            f"chunk checksum failed for {chunk_type!r}: {chunk_crc} != {checksum}"
        )

    return ChunkRecord(
        offset=-1,
        type=chunk_type,
        data=chunk_data,
        crc=chunk_crc,
        crc_ok=crc_ok,
    )


def parse_png(path: str, verify_crc: bool = True) -> ParseResult:
    """Parse a PNG file and return structured metadata."""
    file_size = os.path.getsize(path)
    result = ParseResult(path=path, file_size=file_size, signature_ok=False)

    with open(path, "rb") as file:
        signature = file.read(len(PNG_SIGNATURE))
        result.signature_ok = signature == PNG_SIGNATURE
        if not result.signature_ok:
            result.errors.append("invalid_png_signature")
            file.seek(0)

        offset = len(PNG_SIGNATURE) if result.signature_ok else 0

        while True:
            try:
                chunk = read_chunk(file, verify_crc=verify_crc)
            except ValueError as exc:
                result.errors.append(str(exc))
                break

            if chunk is None:
                result.errors.append("unexpected_end_of_file_before_iend")
                break

            chunk.offset = offset
            result.chunks.append(chunk)
            offset += 8 + len(chunk.data) + 4

            if chunk.type == TYPE_IEND:
                break

        result.trailing = file.read()

    if result.has_chunk(TYPE_IHDR):
        ihdr_record = result.chunks_of_type(TYPE_IHDR)[0]
        result.ihdr = ChunkIHDR(
            ihdr_record.type, ihdr_record.data, ihdr_record.crc
        )

    return result


def parse_png_lenient(path: str) -> ParseResult:
    """Parse without raising on the first CRC error (for corrupted test files)."""
    file_size = os.path.getsize(path)
    result = ParseResult(path=path, file_size=file_size, signature_ok=False)

    with open(path, "rb") as file:
        signature = file.read(len(PNG_SIGNATURE))
        result.signature_ok = signature == PNG_SIGNATURE
        if not result.signature_ok:
            result.errors.append("invalid_png_signature")
            file.seek(0)

        offset = len(PNG_SIGNATURE) if result.signature_ok else 0

        while True:
            header = file.read(8)
            if not header:
                result.errors.append("unexpected_end_of_file_before_iend")
                break
            if len(header) < 8:
                result.errors.append("truncated_chunk_header")
                break

            chunk_length, chunk_type = struct.unpack(">I4s", header)
            chunk_data = file.read(chunk_length)
            if len(chunk_data) < chunk_length:
                result.errors.append(f"truncated_chunk_data:{chunk_type!r}")
                break

            crc_bytes = file.read(4)
            if len(crc_bytes) < 4:
                result.errors.append(f"truncated_crc:{chunk_type!r}")
                break

            chunk_crc, = struct.unpack(">I", crc_bytes)
            checksum = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
            crc_ok = chunk_crc == checksum
            if not crc_ok:
                result.errors.append(
                    f"chunk_checksum_failed:{chunk_type.decode('latin-1')}"
                )

            result.chunks.append(
                ChunkRecord(
                    offset=offset,
                    type=chunk_type,
                    data=chunk_data,
                    crc=chunk_crc,
                    crc_ok=crc_ok,
                )
            )
            offset += 8 + len(chunk_data) + 4

            if chunk_type == TYPE_IEND:
                break

        result.trailing = file.read()

    if result.has_chunk(TYPE_IHDR):
        ihdr_record = result.chunks_of_type(TYPE_IHDR)[0]
        try:
            result.ihdr = ChunkIHDR(
                ihdr_record.type, ihdr_record.data, ihdr_record.crc
            )
        except Exception as exc:
            result.errors.append(f"ihdr_parse_error:{exc}")

    return result
