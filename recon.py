
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