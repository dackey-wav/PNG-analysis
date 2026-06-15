from chunktypes import TYPE_IDAT
from console import field_line


def format_idat_summary(chunks) -> str:
    idat_data = [data for chunk_type, data, _ in chunks if chunk_type == TYPE_IDAT]
    count = len(idat_data)
    total = sum(len(data) for data in idat_data)
    if idat_data:
        first_bytes = idat_data[0][:2].hex(" ")
    else:
        first_bytes = "n/a"
    return "\n".join(
        [
            field_line("Chunks", str(count)),
            field_line("Compressed size", f"{total} bytes"),
            field_line("First bytes", first_bytes),
        ]
    )
