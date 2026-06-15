from __future__ import annotations

from color import Color


def c(color: Color, text: str) -> str:
    return f"{color.value}{text}{Color.reset.value}"


def heading(text: str) -> str:
    return c(Color.line, text)


def section(text: str) -> str:
    return c(Color.line, f"{text}:")


def label(text: str) -> str:
    return c(Color.id, text)


def chunk_type(text: str, *, critical: bool) -> str:
    return c(Color.chunk if critical else Color.text, text)


def metric_name(text: str) -> str:
    return c(Color.length, text)


def ok(text: str = "OK") -> str:
    return c(Color.text, text)


def fail(text: str = "FAIL") -> str:
    return c(Color.unknown, text)


def warn(text: str) -> str:
    return c(Color.unknown, text)


def field_line(name: str, value: str) -> str:
    return f"  {label(name):<{18}} {value}"


def format_chunk_row(
    offset: int,
    name: str,
    length: int,
    role: str,
    *,
    critical: bool,
    crc_ok_flag: bool,
) -> str:
    crc_text = ok("OK") if crc_ok_flag else fail("FAIL")
    role_text = chunk_type(role, critical=critical)
    return (
        f"  {label(f'0x{offset:04X}'):<{14}} "
        f"{chunk_type(name, critical=critical):4}  "
        f"{metric_name(f'len={length:5d}')}  "
        f"{role_text:9}  "
        f"{label('crc')}={crc_text}"
    )
