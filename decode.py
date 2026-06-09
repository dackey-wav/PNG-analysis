import struct
import zlib

file = open("data/wierd.png", "rb")

PngSignature = b'\x89PNG\r\n\x1a\n'
if file.read(len(PngSignature)) != PngSignature:
    raise Exception('Invalid PNG Signature')
else:
    print('PNG is OK')

def read_chuks(f):
    '''Returns (chunk_type, chunk_data)'''

    chunk_length, chunk_type = struct.unpack('>I4s', f.read(8))
    chunk_data = f.read(chunk_length)
    checksum = zlib.crc32(chunk_data, zlib.crc32(struct.pack('>4s', chunk_type)))
    chunk_crc, = struct.unpack('>I', f.read(4))
    if chunk_crc != checksum:
        raise Exception('chunk checksum failed {} != {}'.format(chunk_crc,
            checksum))
    return chunk_type, chunk_data

chunks = []
while True:
    chunk_type, chunk_data = read_chuks(file)
    chunks.append((chunk_type, chunk_data))
    if chunk_type == b'IEND':
        break

# print([(chunk_type, chunk_data) for chunk_type, chunk_data in chunks])

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

_, IHDR_data = chunks[0]
width, height, bitd, colort, compm, filterm, interlacem = struct.unpack('>IIBBBBB', IHDR_data)
print(width, height, bitd, colort, compm, filterm, interlacem)

# if compm != 0:
#     raise Exception('invalid compression method')
# if filterm != 0:
#     raise Exception('invalid filter method')

# if colort != 6:
#     raise Exception('we only support truecolor with alpha')
# if bitd != 8:
#     raise Exception('we only support a bit depth of 8')
# if interlacem != 0:
#     raise Exception('we only support no interlacing')

# print(width, height)


IDAT_data = b''.join(chunk_data for chunk_type, chunk_data in chunks if chunk_type == b'IDAT')
IDAT_data = zlib.decompress(IDAT_data)

print(len(IDAT_data))


'''
Filters operate on the byte sequence formed by the scanline. 
The exhaustive list of filter types is:


Type | Name	   | Filter Function	                        | Reconstruction Function
___________________________________________________________________________________________________________
0	 | None	   | Filt(x) = Orig(x)                          | Recon(x) = Filt(x)

1	 | Sub	   | Filt(x) = Orig(x) - Orig(a)	            | Recon(x) = Filt(x) + Recon(a)

2	 | Up	   | Filt(x) = Orig(x) - Orig(b)                | Recon(x) = Filt(x) + Recon(b)

3	 | Average | Filt(x) = Orig(x) -                        | Recon(x) = Filt(x) +
     |         |  floor((Orig(a) + Orig(b)) / 2)      	    |  floor((Recon(a) + Recon(b)) / 2)

4	 | Paeth   | Filt(x) = Orig(x) - 	                    | Recon(x) = Filt(x) +
     |         |  PaethPredictor(Orig(a), Orig(b), Orig(c)) |  PaethPredictor(Recon(a), Recon(b), Recon(c))

where:

    x is the byte being filtered
    a is the byte corresponding to x in the pixel immediately before the pixel containing x 
        (or 0 if such a pixel is out of bounds of the image)
    b is the byte corresponding to x in the previous scanline 
        (or 0 if such a scanline is out of bounds of the image)
    c is the byte corresponding to b in the pixel immediately before the pixel containing b 
        (or 0 if such a pixel is out of bounds of the image)
'''

def PaethPredictor(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        Pr = a
    elif pb <= pc:
        Pr = b
    else:
        Pr = c
    return Pr

Recon = []

bytesPerPixel = 4
stride = width * bytesPerPixel

# r - scanline index of the byte being reconstructed
# c - index of that byte along the scanline
def Recon_a(r, c):
    return Recon[r * stride + c - bytesPerPixel] if c >= bytesPerPixel else 0

def Recon_b(r, c):
    return Recon[(r-1) * stride + c] if r > 0 else 0

def Recon_c(r, c):
    return Recon[(r-1) * stride + c - bytesPerPixel] if r > 0 and c >= bytesPerPixel else 0

i = 0
for r in range(height): # for each scanline
    filter_type = IDAT_data[i] # first byte of scanline is filter type
    i += 1
    for c in range(stride): # for each byte in scanline
        Filt_x = IDAT_data[i]
        i += 1
        if filter_type == 0: # None
            Recon_x = Filt_x
        elif filter_type == 1: # Sub
            Recon_x = Filt_x + Recon_a(r, c)
        elif filter_type == 2: # Up
            Recon_x = Filt_x + Recon_b(r, c)
        elif filter_type == 3: # Average
            Recon_x = Filt_x + (Recon_a(r, c) + Recon_b(r, c)) // 2
        elif filter_type == 4: # Paeth
            Recon_x = Filt_x + PaethPredictor(Recon_a(r, c), Recon_b(r, c), Recon_c(r, c))
        else:
            raise Exception('unknown filter type: ' + str(filter_type))
        Recon.append(Recon_x & 0xff) # truncation to byte


import matplotlib.pyplot as plt
import numpy as np
plt.imshow(np.array(Recon).reshape((height, width, 4)))
plt.show()