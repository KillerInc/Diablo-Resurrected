#!/usr/bin/env python3
"""Check HUD persistence in GPU images from the extended SDL3 replay.

Requires Pillow. Compare the unchanged CHAR button with the restored Classic
frame, rather than assuming that a successful replay means its HUD was drawn.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageChops


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', type=Path, required=True)
    args = parser.parse_args()
    reference_path = args.captures / 'gpu-2650-Classic.png'
    with Image.open(reference_path) as source:
        reference = source.convert('RGB')
    width, height = reference.size
    left, top = (width - 640) // 2, height - 128
    button = (left + 6, top + 5, left + 80, top + 26)
    expected = reference.crop(button)
    checked = 0
    for frame in (2150, 2250, 2350):
        path = args.captures / f'gpu-{frame}-HD.png'
        with Image.open(path) as source:
            actual = source.convert('RGB')
        if actual.size != reference.size:
            raise SystemExit(f'Unexpected GPU frame dimensions: {path.name}')
        if ImageChops.difference(actual.crop(button), expected).getbbox() is not None:
            raise SystemExit(f'HUD disappeared or changed during zoom: {path.name}')
        checked += 1
    print(f'HUD persistence verified in all {checked} zoomed GPU frames against Classic restoration')


if __name__ == '__main__':
    main()
