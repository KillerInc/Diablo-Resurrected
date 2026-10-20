#!/usr/bin/env python3
"""Build a version-matched MPQ from CMake-staged DevilutionX source assets.

The standalone devilutionx-assets release does not necessarily contain the
ASSETS_VERSION file expected by the game. This builds the support MPQ from
the same pinned source tree as the executable instead. All input resources
are open-source engine support data; no copyrighted Blizzard files.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import struct

MASK32 = 0xFFFFFFFF
FILE_EXISTS = 0x80000000
FILE_SINGLE_UNIT = 0x01000000


def make_crypt_table() -> list[int]:
    table = [0] * 0x500
    seed = 0x00100001
    for index in range(0x100):
        for group in range(5):
            seed = (seed * 125 + 3) % 0x2AAAAB
            high = (seed & 0xFFFF) << 16
            seed = (seed * 125 + 3) % 0x2AAAAB
            table[group * 0x100 + index] = high | (seed & 0xFFFF)
    return table


CRYPT = make_crypt_table()


def mpq_hash(name: str, hash_type: int) -> int:
    seed1, seed2 = 0x7FED7FED, 0xEEEEEEEE
    for value in name.replace('/', '\\').upper().encode('ascii'):
        seed1 = (CRYPT[hash_type * 0x100 + value] ^ (seed1 + seed2)) & MASK32
        seed2 = (value + seed1 + seed2 + (seed2 << 5) + 3) & MASK32
    return seed1


def encrypt_words(data: bytes, key: int) -> bytes:
    assert len(data) % 4 == 0
    output = bytearray(len(data))
    seed1, seed2 = key, 0xEEEEEEEE
    for offset in range(0, len(data), 4):
        value = struct.unpack_from('<I', data, offset)[0]
        seed2 = (seed2 + CRYPT[0x400 + (seed1 & 0xFF)]) & MASK32
        struct.pack_into('<I', output, offset, (value ^ (seed1 + seed2)) & MASK32)
        seed1 = (((~seed1 << 21) + 0x11111111) | (seed1 >> 11)) & MASK32
        seed2 = (value + seed2 + (seed2 << 5) + 3) & MASK32
    return bytes(output)


def decrypt_words(data: bytes, key: int) -> bytes:
    if len(data) % 4:
        raise ValueError('MPQ table length must be divisible by four')
    output = bytearray(len(data))
    seed1, seed2 = key, 0xEEEEEEEE
    for offset in range(0, len(data), 4):
        seed2 = (seed2 + CRYPT[0x400 + (seed1 & 0xFF)]) & MASK32
        cipher = struct.unpack_from('<I', data, offset)[0]
        plain = (cipher ^ (seed1 + seed2)) & MASK32
        struct.pack_into('<I', output, offset, plain)
        seed1 = (((~seed1 << 21) + 0x11111111) | (seed1 >> 11)) & MASK32
        seed2 = (plain + seed2 + (seed2 << 5) + 3) & MASK32
    return bytes(output)


def build_support_mpq(assets: Path, destination: Path) -> None:
    paths = sorted((p for p in assets.rglob('*') if p.is_file()),
                   key=lambda p: p.relative_to(assets).as_posix().casefold())
    if not paths:
        raise ValueError(f'No staged assets found in {assets}')
    if (assets / 'ASSETS_VERSION').read_bytes() != b'1\n':
        raise ValueError('Missing or incompatible source ASSETS_VERSION')

    names = [p.relative_to(assets).as_posix().replace('/', '\\') for p in paths]
    if len(names) != len({name.upper() for name in names}):
        raise ValueError('Duplicate case-insensitive asset paths')
    if '(listfile)' in {name.lower() for name in names}:
        raise ValueError('Reserved (listfile) exists in input assets')
    listfile = ('\r\n'.join(names + ['(listfile)']) + '\r\n').encode('ascii')
    entries = [(name, path.read_bytes()) for name, path in zip(names, paths)]
    entries.append(('(listfile)', listfile))

    hash_count = 1
    while hash_count < len(entries) * 2:
        hash_count *= 2
    hashes = [b'\xff' * 16 for _ in range(hash_count)]
    blocks = []
    payloads = bytearray()
    for block_index, (name, payload) in enumerate(entries):
        offset = 32 + len(payloads)
        if offset + len(payload) >= 2**32:
            raise ValueError('MPQ v0 cannot store >=4 GiB of asset data')
        payloads.extend(payload)
        blocks.append(struct.pack('<IIII', offset, len(payload), len(payload),
                                  FILE_EXISTS | FILE_SINGLE_UNIT))
        slot = mpq_hash(name, 0) % hash_count
        while hashes[slot] != b'\xff' * 16:
            slot = (slot + 1) % hash_count
        hashes[slot] = struct.pack('<IIHHI', mpq_hash(name, 1), mpq_hash(name, 2),
                                  0, 0, block_index)

    hash_offset = 32 + len(payloads)
    hash_table = encrypt_words(b''.join(hashes), mpq_hash('(hash table)', 3))
    block_offset = hash_offset + len(hash_table)
    block_table = encrypt_words(b''.join(blocks), mpq_hash('(block table)', 3))
    length = block_offset + len(block_table)
    header = struct.pack('<4sIIHHIIII', b'MPQ\x1a', 32, length, 0, 3,
                         hash_offset, block_offset, hash_count, len(entries))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(header + payloads + hash_table + block_table)
    print(f'Packed {len(paths)} source assets: {destination} ({length} bytes)')


def verify_support_mpq(destination: Path) -> None:
    """Verify startup files by decrypting the actual generated MPQ tables."""
    raw = destination.read_bytes()
    if len(raw) < 32:
        raise ValueError('Truncated support archive')
    magic, size, file_length, version, sector, hp, bp, hc, bc = struct.unpack_from(
        '<4sIIHHIIII', raw)
    if (magic, size, file_length, version) != (b'MPQ\x1a', 32, len(raw), 0):
        raise ValueError('Incorrect support MPQ header')
    if hc < 2 or hc & (hc - 1) or not bc:
        raise ValueError('Incorrect support MPQ table counts')
    if hp + hc * 16 > len(raw) or bp + bc * 16 > len(raw):
        raise ValueError('Support MPQ table outside file')
    hash_table = decrypt_words(raw[hp:hp + hc * 16], mpq_hash('(hash table)', 3))
    block_table = decrypt_words(raw[bp:bp + bc * 16], mpq_hash('(block table)', 3))
    for name, expected in [('ASSETS_VERSION', b'1\n'),
                           ('data\\charbg.clx', None),
                           ('(listfile)', None)]:
        slot = mpq_hash(name, 0) % hc
        a, b = mpq_hash(name, 1), mpq_hash(name, 2)
        for _ in range(hc):
            x, y, locale, index = struct.unpack_from('<IIII', hash_table, slot * 16)
            if index == 0xFFFFFFFF:
                raise ValueError(f'Missing required support asset: {name}')
            if (x, y) == (a, b):
                if index >= bc:
                    raise ValueError(f'Invalid support asset index: {name}')
                offset, packed, original, flags = struct.unpack_from(
                    '<IIII', block_table, index * 16)
                if not flags & FILE_EXISTS or offset + packed > len(raw):
                    raise ValueError(f'Invalid support asset block: {name}')
                if expected is not None and (
                    packed != original or raw[offset:offset + original] != expected
                ):
                    raise ValueError(f'Wrong support asset contents: {name}')
                break
            slot = (slot + 1) % hc
        else:
            raise ValueError(f'Missing support asset: {name}')
    print(f'Verified ASSETS_VERSION and UI resources in {destination}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build_support_mpq(args.assets, args.output)
    verify_support_mpq(args.output)


if __name__ == '__main__':
    main()
