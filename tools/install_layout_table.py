"""Install a tested executable and migrate runtime sidecars to one HD table.
Exact executable, sidecar and manifest backups support rollback on any failure.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
from hd_layouts import collect, read_table, write_table, key


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest().upper()


def install(binary, game, manifest, mirror_manifest, backup):
    binary, game, manifest, mirror_manifest, backup = map(Path, (binary, game, manifest, mirror_manifest, backup))
    hd = (game / 'HD').resolve()
    target = game / 'Diablo Reincarnated.exe'
    table = hd / 'layouts.csv'
    assert binary.is_file() and target.is_file() and not table.exists() and not backup.exists()
    before = manifest.read_bytes()
    mirror_before = mirror_manifest.read_bytes()
    current = json.loads(before)
    assert json.loads(mirror_before) == current
    rows = collect(hd)
    sidecars = list(hd.rglob('*.layout'))
    assert len(sidecars) == len(rows) and rows
    images = {name: sha(hd / name) for name in rows}
    for name, record in current['sheets'].items():
        relative = key('plrgfx/warrior/' + name[:3] + '/' + name + '.png')
        assert rows[relative] == record['layout'] and images[relative] == record['sha256'].upper(), name
    old_exe, new_exe = sha(target), sha(binary)
    assert old_exe != new_exe
    backup.mkdir(parents=True)
    shutil.copy2(target, backup / 'Diablo Reincarnated.before-0.4.3.exe')
    (backup / 'previous-install-manifest.json').write_bytes(before)
    (backup / 'previous-mirror-manifest.json').write_bytes(mirror_before)
    for path in sidecars:
        relative = path.resolve().relative_to(hd)
        dest = backup / 'sidecars' / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    replaced = False
    temporary = target.with_name(target.name + '.new')
    try:
        write_table(table, rows)
        assert read_table(table) == rows
        shutil.copy2(binary, temporary)
        os.replace(temporary, target)
        replaced = True
        for path in sidecars:
            path.resolve().relative_to(hd)
            path.unlink()
        assert not list(hd.rglob('*.layout'))
        assert all(sha(hd / name) == value for name, value in images.items())
        assert sha(target) == new_exe
        receipt = {'version': '0.4.3-pre', 'layout_file': str(table), 'layout_sha256': sha(table),
                   'layout_rows': len(rows), 'removed_sidecars': len(sidecars), 'custom_sheet_count': len(current['sheets']),
                   'executable_sha256': new_exe, 'previous_executable_sha256': old_exe,
                   'backup': str(backup), 'png_hashes_preserved': images, 'cache': 'process-lifetime',
                   'individual_layout_runtime_support': False}
        updated = copy.deepcopy(current)
        updated['version'] = receipt['version']
        updated['layout_table_revision'] = receipt
        updated['layout_table'] = {'path': str(table), 'sha256': sha(table), 'rows': len(rows)}
        data = json.dumps(updated, indent=2).encode('utf-8')
        manifest.write_bytes(data)
        mirror_manifest.write_bytes(data)
        (backup / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        print('Installed 0.4.3-pre;', len(rows), 'layouts consolidated; all PNGs preserved; individual runtime layouts removed')
    except BaseException:
        for path in sidecars:
            shutil.copy2(backup / 'sidecars' / path.relative_to(hd), path)
        if replaced:
            shutil.copy2(backup / 'Diablo Reincarnated.before-0.4.3.exe', target)
        table.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)
        manifest.write_bytes(before)
        mirror_manifest.write_bytes(mirror_before)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['binary', 'game', 'manifest', 'mirror_manifest', 'backup']:
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    install(args.binary, args.game, args.manifest, args.mirror_manifest, args.backup)
