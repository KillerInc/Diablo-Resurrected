#!/usr/bin/env python3
"""Generate original, synthetic Warrior HD artwork for testing F10 (no Blizzard assets)."""
import argparse
from pathlib import Path
import struct
import zlib


def chunk(kind: bytes, data: bytes) -> bytes:
    return (struct.pack("!I", len(data)) + kind + data
            + struct.pack("!I", zlib.crc32(kind + data) & 0xffffffff))


def pixel(x: int, y: int, width: int, height: int) -> bytes:
    # Deliberately conspicuous 2D armor silhouette with transparent margins.
    dx = (x - width // 2) / width
    dy = y / height
    glow = dx * dx * 2.4 + ((dy - .42) * .75) ** 2 < .20
    head = (dx / .105) ** 2 + ((dy - .22) / .11) ** 2 < 1
    chest = .34 < dy < .70 and abs(dx) < .22 - .08 * (dy - .34)
    arm = .39 < dy < .67 and .18 < abs(dx) < .29
    legs = .65 < dy < .93 and .045 < abs(dx) < .17
    if not (head or chest or arm or legs or glow):
        return bytes((0, 0, 0, 0))
    if head:
        return bytes((250, 207, 120, 255))
    if chest:
        return bytes((224, 76, 27, 255))
    if arm:
        return bytes((246, 140, 46, 255))
    if legs:
        return bytes((83, 134, 183, 255))
    return bytes((255, 130, 20, 72))


def write_png(path: Path, width: int, height: int) -> None:
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.extend(pixel(x, y, width, height))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!2I5B", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 7))
        + chunk(b"IEND", b""))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("."), help="Game working directory")
    args = parser.parse_args()
    destination = args.out / "hd" / "players"
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "0.png"  # HeroClass::Warrior
    write_png(path, 384, 512)
    # No .layout override: retain the original per-frame Warrior draw footprint.
    print(f"Created synthetic 384x512 RGBA Warrior override: {path}")


if __name__ == "__main__":
    main()
