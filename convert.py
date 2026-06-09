from PIL import Image
import pillow_heif
import argparse
from pathlib import Path

pillow_heif.register_heif_opener()

def convert_heic(path: str):
    src = Path(path)
    out = src.with_suffix(".png")
    img = Image.open(path)
    img.save(out, format="PNG")

    return out


def main(path: str):
    return convert_heic(path)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert a HEIC image to PNG.")
    parser.add_argument("path", type=str, help="Path to the image to convert.")

    args = parser.parse_args()
    path = args.path
    main(path)