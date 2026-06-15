import struct

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
    '0': ([1, 2, 4, 8, 16], 'Grayscale'),
    '2': ([8, 16], 'RGB'),
    '3': ([1, 2, 4, 8], 'Pallete'),
    '4': ([8, 16], 'Grayscale with alpha'),
    '6': ([8, 16], 'RGBA')
}

COLOR_TYPE_PALLETE = 3


class ChunkIHDR:
    def __init__(self, type_: bytes, data: bytes, crc: int) -> None:
        self.type = type_
        self.crc = crc

        values = struct.unpack('>IIBBBBB', data)

        self.width = values[0]
        self.height = values[1]
        self.bitd = values[2]
        self.colort = values[3]
        self.compm = values[4]
        self.filterm = values[5]
        self.interlacem = values[6]

        self.color_type_display = ''
        self.check_color_type()

    def check_color_type(self) -> None:
        color_type = str(self.colort)
        if color_type in COLOR_TYPE:
            color = COLOR_TYPE[color_type]

            if self.bitd not in color[0]:
                print("Bit depth not allowed for this color type.")

            self.color_type_display = (
                f"Color type is {self.colort} ({color[1]}). "
                f"Allowed bit depths: {color[0]}"
            )

    def use_pallete(self) -> bool:
        return self.colort == COLOR_TYPE_PALLETE

    def color_type_name(self) -> str:
        color = COLOR_TYPE.get(str(self.colort))
        return color[1] if color else "Unknown"

    def __str__(self) -> str:
        ret = f'Size :           {self.width} × {self.height}\n' \
              f'Bit depth :      {self.bitd} {"bits" if self.bitd > 1 else "bit"} per sample\n' \
              f'Color type :     {self.colort} - {self.color_type_name()}\n' \
              f'Compression :    {self.compm} - deflate\n' \
              f'Filter :         {self.filterm} - adaptive filtering with five basic filter types\n' \
              f'Interlace :      {self.interlacem} - {"Adam7" if self.interlacem == 1 else "none"}\n'
        return ret