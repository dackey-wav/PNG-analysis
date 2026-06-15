from console import field_line, label

PIXEL_LEN = 3


class ChunkPLTE:
    def __init__(self, type_: bytes, data: bytes, crc: int) -> None:
        self.type = type_
        self.crc = crc

        self.palette = []
        for i in range(0, len(data), PIXEL_LEN):
            pixel = tuple(data[i : i + PIXEL_LEN])
            self.palette.append(pixel)

    def __str__(self) -> str:
        lines = [field_line("Entries", str(len(self.palette)))]
        for i, pixel in enumerate(self.palette[:5]):
            r, g, b = pixel
            lines.append(f"  {label(f'[{i}]')} RGB({r}, {g}, {b})")
        if len(self.palette) > 5:
            lines.append(f"  {label('...')} ({len(self.palette) - 5} more)")
        return "\n".join(lines)
