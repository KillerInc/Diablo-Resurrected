"""Install validated private UI BC7 resources without changing existing art."""
import argparse
import json
import os
from pathlib import Path
import shutil
from gpu_index import read_index
from install_terrain_pack import sha

UI_PREFIXES = ('ctrlpan/', 'data/', 'items/', 'ui_art/', 'gendata/')


def install(staged_hd, game_hd, backup, validation):
    staged_hd, game_hd, backup, validation = map(Path, (staged_hd, game_hd, backup, validation))
    proof = json.loads(validation.read_text(encoding='utf-8'))
    assert all(proof['checks'][name] for name in ('ui_gpu_readback', 'full_pack_gpu_upload',
        'gameplay_reference_same', 'gameplay_reference_repeat_same', 'png_free_runtime'))
    ui = proof['ui_pack']
    old_path, new_path = game_hd/'sprites.gpus', staged_hd/'sprites.gpus'
    assert sha(old_path) == ui['previous_index_sha256']
    assert sha(new_path) == ui['index_sha256']
    old, new = read_index(old_path), read_index(new_path)
    added = set(new)-set(old)
    assert added == set(ui['resources']) and added
    assert all(key.startswith(UI_PREFIXES) for key in added)
    assert all(new.get(key) == record for key, record in old.items()), 'Existing records must remain identical'
    assert not backup.exists(), 'Use a fresh executable/pack backup directory'
    pages = []
    for key in sorted(added):
        record = new[key]; count = int(record[0].split()[-1])
        for line in record[1:1+count]:
            name = line.split()[0]
            assert Path(name).name == name and '/' not in name and chr(92) not in name
            relative = Path(key).parent/name
            source, target = staged_hd/relative, game_hd/relative
            assert target.resolve().is_relative_to(game_hd.resolve())
            expected = ui['page_hashes'][relative.as_posix()]
            assert sha(source) == expected
            assert not target.exists() or sha(target) == expected, 'Refusing to overwrite unknown art'
            pages.append((source, target, expected))
    previous = old_path.read_bytes(); backup.mkdir(parents=True)
    (backup/'previous-sprites.gpus').write_bytes(previous)
    temporary = old_path.with_name('sprites.gpus.new')
    assert not temporary.exists()
    try:
        for source, target, expected in pages:
            if target.exists(): continue
            target.parent.mkdir(parents=True, exist_ok=True)
            staging = target.with_name(target.name+'.new'); assert not staging.exists()
            shutil.copy2(source, staging); assert sha(staging) == expected
            os.replace(staging, target)
        temporary.write_bytes(new_path.read_bytes()); os.replace(temporary, old_path)
        assert read_index(old_path) == new
        receipt = {'sheets_before':len(old),'sheets_after':len(new),'ui_sheets':len(added),
            'ui_pages':len(pages),'existing_records_preserved':True,'index_sha256':sha(old_path)}
        (backup/'receipt.json').write_text(json.dumps(receipt,indent=2))
        print(json.dumps(receipt))
    except BaseException:
        old_path.write_bytes(previous); temporary.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('staged_hd','game_hd','backup','validation'):parser.add_argument(name,type=Path)
    args=parser.parse_args();install(args.staged_hd,args.game_hd,args.backup,args.validation)
