import struct

from console import field_line

'''
PNG Image Type | Color type | Allowed bit depths | Interpretation
____________________________________________________________________________________
Grayscale      | 0	        | 1, 2, 4, 8, 16	 | Each pixel is a grayscale sample.

Truecolor	   | 2          | 8, 16	             | Each pixel is a R,G,B triple.

Indexed-color  | 3	        | 1, 2, 4, 8	     | Each pixel is a palette index; 
               |                                 |  a PLTE chunk shall appear.

Grayscale with | 4	        | 8, 16	             | Each pixel is a grayscale sample 
alpha	       |                                 |  followed by an alpha sample.


Truecolor with | 6	        | 8, 16	             | Each pixel is a R,G,B triple
alpha          |                                 |  followed by an alpha sample.
'''

COLOR_TYPE = {
    "0": ([1, 2, 4, 8, 16], "Grayscale"),
    "2": ([8, 16], "RGB"),
    "3": ([1, 2, 4, 8], "Pallete"),
    "4": ([8, 16], "Grayscale with alpha"),
    "6": ([8, 16], "RGBA"),
}

COLOR_TYPE_PALLETE = 3


class ChunkIHDR:
    def __init__(self, type_: bytes, data: bytes, crc: int) -> None:
        self.type = type_
        self.crc = crc

        values = struct.unpack(">IIBBBBB", data)

        self.width = values[0]
        self.height = values[1]
        self.bitd = values[2]
        self.colort = values[3]
        self.compm = values[4]
        self.filterm = values[5]
        self.interlacem = values[6]

        self.bit_depth_warning = False
        self._validate_color_type()

    def _validate_color_type(self) -> None:
        color_type = str(self.colort)
        if color_type in COLOR_TYPE and self.bitd not in COLOR_TYPE[color_type][0]:
            self.bit_depth_warning = True

    def use_pallete(self) -> bool:
        return self.colort == COLOR_TYPE_PALLETE

    def color_type_name(self) -> str:
        color = COLOR_TYPE.get(str(self.colort))
        return color[1] if color else "Unknown"

    def __str__(self) -> str:
        bit_label = "bits" if self.bitd > 1 else "bit"
        lines = [
            field_line("Size", f"{self.width} × {self.height}"),
            field_line("Bit depth", f"{self.bitd} {bit_label} per sample"),
            field_line(
                "Color type",
                f"{self.colort} - {self.color_type_name()}",
            ),
            field_line("Compression", f"{self.compm} - deflate"),
            field_line(
                "Filter",
                f"{self.filterm} - adaptive filtering with five basic filter types",
            ),
            field_line(
                "Interlace",
                f"{self.interlacem} - {'Adam7' if self.interlacem == 1 else 'none'}",
            ),
        ]
        return "\n".join(lines)
