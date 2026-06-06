import struct
import zlib

file = open("data/photo.png", "rb")

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

print([chunk_type for chunk_type, chunk_data in chunks])