"""Install only the five validated terrain records; preserve every existing sprite.

Input art and this tool's receipts stay private. No PNGs or per-sheet metadata
are installed. Renderer installation and executable backups are separate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from gpu_index import read_index

TERRAIN = tuple('levels/' + stem + '.png' for stem in (
    'l1data/l1', 'l2data/l2', 'l3data/l3', 'l4data/l4', 'towndata/town'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def install(staged_hd, game_hd, backup, validation):
    staged_hd, game_hd, backup, validation = map(Path, (staged_hd, game_hd, backup, validation))
    proof = json.loads(validation.read_text())
    checks = proof['checks']
    assert all(checks[name] for name in ('terrain_gpu_readback', 'full_pack_gpu_upload',
               'gameplay_reference_same', 'gameplay_reference_repeat_same', 'png_free_runtime'))
    current_index, staged_index = game_hd/'sprites.gpus', staged_hd/'sprites.gpus'
    assert sha(current_index) == proof['terrain']['previous_index_sha256']
    assert sha(staged_index) == proof['terrain']['pack_file_hashes']['sprites.gpus']
    current, staged = read_index(current_index), read_index(staged_index)
    assert set(staged)-set(current) == set(TERRAIN)
    assert all(staged[key] == value for key, value in current.items())
    assert not backup.exists(), 'A fresh backup directory is required'
    pages = []
    for key in TERRAIN:
        record = staged[key]; count = int(record[0].split()[-1])
        for line in record[1:1+count]:
            name = line.split()[0]
            assert Path(name).name == name and '/' not in name and chr(92) not in name
            relative = Path(key).parent/name
            source, target = staged_hd/relative, game_hd/relative
            assert target.resolve().is_relative_to(game_hd.resolve())
            expected = proof['terrain']['pack_file_hashes'][relative.as_posix()]
            assert sha(source) == expected
            assert not target.exists() or sha(target) == expected, 'Refusing to overwrite unknown art'
            pages.append((source, target, expected))
    previous = current_index.read_bytes(); backup.mkdir(parents=True)
    (backup/'previous-sprites.gpus').write_bytes(previous)
    try:
        for source, target, expected in pages:
            if target.exists(): continue
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name+'.new')
            assert not temporary.exists()
            shutil.copy2(source, temporary)
            assert sha(temporary) == expected
            os.replace(temporary, target)
        temporary = current_index.with_name('sprites.gpus.new')
        assert not temporary.exists()
        temporary.write_bytes(staged_index.read_bytes()); os.replace(temporary, current_index)
        assert read_index(current_index) == staged
        receipt = {'sheets_before': len(current), 'sheets_after': len(staged),
                   'terrain_pages': len(pages), 'original_records_preserved': True,
                   'index_sha256': sha(current_index)}
        (backup/'receipt.json').write_text(json.dumps(receipt, indent=2))
        print(json.dumps(receipt))
    except BaseException:
        current_index.write_bytes(previous)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('staged_hd', 'game_hd', 'backup', 'validation'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args(); install(args.staged_hd, args.game_hd, args.backup, args.validation)
