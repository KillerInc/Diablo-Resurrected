#!/usr/bin/env python3
"""Prepare an isolated Warrior replay for Windows SDL3 launch validation.

Uses the upstream shareware Warrior save fixture, never an installed user's
save. Game data is not copied. Run the packaged game with --spawn --demo 1
--save-dir OUTPUT --config-dir OUTPUT --data-dir YOUR_DIABLO_FOLDER -n.
Without --timedemo each phase lasts 15 seconds for visual inspection:
Classic, HD Warrior, Escape menu over HD, HD again, then Classic and exit.
"""
import argparse
from pathlib import Path
import shutil
import struct


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    fixture = Path(__file__).resolve().parents[1] / 'test/fixtures/timedemo/WarriorLevel1to2'
    # Version 3: version byte, save slot, width/height, 23 gameplay settings.
    header = (fixture / 'demo_0.dmo').read_bytes()[:32]
    if len(header) != 32 or header[0] != 3:
        raise ValueError('Expected the upstream version 3 demo fixture')
    args.out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fixture / 'spawn_0.sv', args.out / 'spawn_0.sv')

    def key(symbol):
        return (struct.pack('<BBIH', 13, 0, symbol, 0)
                + struct.pack('<BBIH', 14, 0, symbol, 0))

    ticks = bytes((0, 0)) * 300
    f10 = key(0x40000043)
    escape = key(27)
    replay = header + ticks + f10 + ticks + escape + ticks + escape + ticks + f10 + ticks + bytes((8, 0))
    (args.out / 'demo_1.dmo').write_bytes(replay)
    # This is an isolated test configuration, not the normal per-user config.
    (args.out / 'diablo.ini').write_text(
        '[Graphics]\nFullscreen=0\nUpscale=1\nFit to Screen=0\n'
        'Width=768\nHeight=480\nHardware Cursor=0\n'
        '[Diablo]\nIntro=0\n', encoding='utf-8')
    print(f'Prepared Classic/HD/menu/Classic replay in {args.out}')


if __name__ == '__main__':
    main()
