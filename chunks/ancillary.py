import base64
import string
import struct
import zlib
import datetime
from typing import Optional, Union

from chunktypes import (
    TYPE_bKGD,
    TYPE_eXIf,
    TYPE_iTXt,
    TYPE_pHYs,
    TYPE_tEXt,
    TYPE_zTXt,
    TYPE_tIME
)
from console import field_line, warn


class ChunkUnknownAncillary:
    def __init__(self, type_: bytes, data: bytes, crc: int) -> None:
        self.type = type_
        self.data = data
        self.crc = crc

    def __str__(self) -> str:
        preview = self.data[:16].hex(" ")
        if len(self.data) > 16:
            preview += " ..."
        return "\n".join(
            [
                field_line("Size", f"{len(self.data)} bytes (not parsed)"),
                field_line("Hex preview", preview),
            ]
        )


class ChunkPhys:
    def __init__(self, type_: bytes, data: bytes, crc: int) -> None:
        self.type = type_
        self.crc = crc

        if len(data) != 9:
            raise ValueError(f"pHYs: expected 9 bytes, got {len(data)}")

        self.px_per_unit_x, self.px_per_unit_y, self.unit = struct.unpack(">IIB", data)

    def __str__(self) -> str:
        if self.unit == 0:
            unit = "unspecified"
            dpi = ""
        elif self.unit == 1:
            unit = "meter"
            dpi_x = self.px_per_unit_x * 0.0254
            dpi_y = self.px_per_unit_y * 0.0254
            dpi = f" (~{dpi_x:.1f} × {dpi_y:.1f} DPI)"
        else:
            unit = f"unknown ({self.unit})"
            dpi = ""

        return field_line(
            "Resolution",
            f"{self.px_per_unit_x} × {self.px_per_unit_y} pixels per {unit}{dpi}",
        )


class ChunkText:
    def __init__(self, type_: bytes, data: bytes, crc: int) -> None:
        self.type = type_
        self.crc = crc

        try:
            key, text = data.split(b"\x00", 1)
            self.key: Optional[str] = key.decode("latin-1", "replace")
            self.text = text.decode("latin-1", "replace")
        except ValueError:
            self.key = None
            self.text = data.decode("latin-1", "replace")

    def __str__(self) -> str:
        return "\n".join(
            [
                field_line("Keyword", self.key or "(none)"),
                field_line("Text", self.text),
            ]
        )


class ChunkZtxt:
    def __init__(self, type_: bytes, data: bytes, crc: int) -> None:
        self.type = type_
        self.crc = crc

        key, rest = data.split(b"\x00", maxsplit=1)
        self.key = key.decode("latin-1", "replace")
        self.method = rest[0]
        if self.method != 0:
            raise ValueError(f"zTXt: unsupported compression method {self.method}")

        self.text = zlib.decompress(rest[1:]).decode("latin-1", "replace")

    def __str__(self) -> str:
        return "\n".join(
            [
                field_line("Keyword", self.key),
                field_line("Method", str(self.method)),
                field_line("Text", self.text),
            ]
        )


class ChunkBkgd:
    def __init__(self, type_: bytes, data: bytes, crc: int) -> None:
        self.type = type_
        self.data = data
        self.crc = crc

    def __str__(self) -> str:
        return field_line("Data", self.data.hex(" "))


class ChunkItxt:
    def __init__(self, type_: bytes, data: bytes, crc: int) -> None:
        self.type = type_
        self.crc = crc

        keyword_end = data.find(b"\x00")
        if keyword_end < 0:
            raise ValueError("iTXt: missing keyword terminator")

        self.keyword = data[:keyword_end].decode("latin-1", "replace")
        self.compression_flag = data[keyword_end + 1]
        self.compression_method = data[keyword_end + 2]

        lang_start = keyword_end + 3
        lang_end = data.find(b"\x00", lang_start)
        if lang_end < 0:
            raise ValueError("iTXt: missing language tag terminator")

        self.language_tag = data[lang_start:lang_end].decode("latin-1", "replace")

        trans_start = lang_end + 1
        trans_end = data.find(b"\x00", trans_start)
        if trans_end < 0:
            raise ValueError("iTXt: missing translated keyword terminator")

        self.translated_keyword = data[trans_start:trans_end].decode("utf-8", "replace")

        text_bytes = data[trans_end + 1:]
        if self.compression_flag == 1:
            if self.compression_method != 0:
                raise ValueError(
                    f"iTXt: unsupported compression method {self.compression_method}"
                )
            self._uncompressed_bytes = zlib.decompress(text_bytes)
        elif self.compression_flag == 0:
            self._uncompressed_bytes = text_bytes
        else:
            raise ValueError(f"iTXt: invalid compression flag {self.compression_flag}")

        self.text = self._uncompressed_bytes.decode("utf-8", errors="replace")

    def __str__(self) -> str:
        decoded_size = len(self._uncompressed_bytes)

        allowed_chars = set(string.printable + "\x00")
        is_printable = all(char in allowed_chars for char in self.text)

        if is_printable and decoded_size > 0:
            preview_text = self.text[:40]
            preview_str = preview_text.replace("\x00", "\\0")
            if len(self.text) > 40:
                preview_str += "..."
            preview = f"'{preview_str}'"
        else:
            b64_str = base64.b64encode(self._uncompressed_bytes[:30]).decode("ascii")
            if decoded_size > 30:
                b64_str += "..."
            preview = f"base64:{b64_str}"

        has_exif_hint = "exif" in self.keyword.lower() or "raw profile" in self.keyword.lower()

        return "\n".join(
            [
                field_line("Keyword", self.keyword),
                field_line("Language", self.language_tag),
                field_line("Translated keyword", self.translated_keyword),
                field_line("Text preview", preview),
                field_line("Decoded size", f"{decoded_size} bytes"),
            ]
            + (
                [field_line("Note", "possible embedded EXIF profile")]
                if has_exif_hint
                else []
            )
        )


class ChunkExif:
    def __init__(self, type_: bytes, data: bytes, crc: int) -> None:
        self.type = type_
        self.crc = crc
        self.data = data
        self.endian: Optional[str] = None
        self.magic: Optional[int] = None
        self.ifd_offset: Optional[int] = None
        self.error: Optional[str] = None

        if len(data) < 8:
            self.error = f"data too short ({len(data)} bytes)"
            return

        if data[:2] == b"II":
            self.endian = "<"
        elif data[:2] == b"MM":
            self.endian = ">"
        else:
            self.error = f"invalid TIFF byte order {data[:2]!r}"
            return

        self.magic, = struct.unpack(self.endian + "H", data[2:4])
        self.ifd_offset, = struct.unpack(self.endian + "I", data[4:8])

    def __str__(self) -> str:
        if self.error:
            return warn(f"eXIf: {self.error}")

        endian_name = "little-endian" if self.endian == "<" else "big-endian"
        magic_ok = "ok" if self.magic == 0x002A else "unexpected"
        return "\n".join(
            [
                field_line("Size", f"{len(self.data)} bytes"),
                field_line("Endian", f"{endian_name} ({self.data[:2]!r})"),
                field_line("TIFF magic", f"0x{self.magic:04X} ({magic_ok})"),
                field_line("IFD offset", str(self.ifd_offset)),
            ]
        )


class ChunkTime:
    def __init__(self, type_: bytes, data: bytes, crc: int) -> None:
        self.type = type_
        self.crc = crc

        values = struct.unpack(">HBBBBB", data)
        self.datetime = datetime.datetime(*values)

    def __str__(self) -> str:
        return field_line("Modified", self.datetime.strftime("%c"))


_ANCILLARY_PARSERS = {
    TYPE_pHYs: ChunkPhys,
    TYPE_tEXt: ChunkText,
    TYPE_zTXt: ChunkZtxt,
    TYPE_iTXt: ChunkItxt,
    TYPE_eXIf: ChunkExif,
    TYPE_bKGD: ChunkBkgd,
    TYPE_tIME: ChunkTime
}


def parse_ancillary(
    chunk_type: bytes, data: bytes, crc: int
) -> Union[
    ChunkPhys,
    ChunkText,
    ChunkZtxt,
    ChunkItxt,
    ChunkExif,
    ChunkBkgd,
    ChunkTime,
    ChunkUnknownAncillary,
    str,
]:
    parser = _ANCILLARY_PARSERS.get(chunk_type)
    if parser is None:
        return ChunkUnknownAncillary(chunk_type, data, crc)

    try:
        return parser(chunk_type, data, crc)
    except Exception as exc:
        name = chunk_type.decode("latin-1", "replace")
        return warn(f"{name}: parse error: {exc}")
