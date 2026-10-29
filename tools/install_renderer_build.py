"""Install a replay-validated renderer build without changing HD art/metadata."""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import shutil
from hd_layouts import read_table
from install_layout_table import sha


def install(binary, game, manifest, mirror_manifest, backup, validation):
    binary, game, manifest, mirror_manifest, backup, validation = map(Path, (binary, game, manifest, mirror_manifest, backup, validation))
    proof = json.loads(validation.read_text())
    version = proof['version']
    assert re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-z0-9]+)?', version)
    assert version == (Path(__file__).resolve().parents[1] / 'REINCARNATED_VERSION').read_text().strip()
    assert proof['executable_sha256'] == sha(binary)
    assert proof['checks'].get('performance_monitor'), 'Performance-monitor replay proof is required'
    assert proof['checks']['provider_tests'] and proof['checks']['integration'] and proof['checks']['gameplay_reference_same']
    assert proof['checks']['warm_player_reloads'] == 0 and proof['checks']['ui_exit'] == 0
    assert proof['checks']['gameplay_reference_repeat_same'] and proof['checks']['other_class_preloads'] == 0
    assert proof['preload']['loaded'] == proof['preload']['resident'] == proof['class_png_count'] > 0 and proof['preload']['skipped'] == 0
    hd = game / 'HD'; table = hd / 'layouts.csv'; target = game / 'Diablo Reincarnated.exe'
    before, mirror_before = manifest.read_bytes(), mirror_manifest.read_bytes()
    current = json.loads(before); assert json.loads(mirror_before) == current and not backup.exists()
    rows = read_table(table); csv_hash = sha(table)
    images = {}
    for name, record in current['sheets'].items():
        relative = 'plrgfx/warrior/' + name[:3] + '/' + name + '.png'
        assert rows[relative] == record['layout']
        images[relative] = sha(hd / relative); assert images[relative] == record['sha256'].upper()
    old_hash = sha(target); backup.mkdir(parents=True)
    old_binary = backup / ('Diablo Reincarnated.before-' + version + '.exe'); shutil.copy2(target, old_binary)
    shutil.copy2(table, backup / 'previous-layouts.csv')
    (backup / 'previous-install-manifest.json').write_bytes(before)
    (backup / 'previous-mirror-manifest.json').write_bytes(mirror_before)
    temporary = target.with_name(target.name + '.new'); replaced = False
    try:
        shutil.copy2(binary, temporary); os.replace(temporary, target); replaced = True
        assert sha(target) == proof['executable_sha256'] and sha(table) == csv_hash
        assert all(sha(hd / name) == digest for name, digest in images.items())
        assert not list(hd.rglob('*.layout'))
        receipt = {'version': version, 'executable_sha256': sha(target), 'previous_executable_sha256': old_hash,
                   'layout_sha256_preserved': csv_hash, 'custom_png_hashes_preserved': images, 'backup': str(backup),
                   'player_preload': proof['preload'], 'validation': proof['checks'],
                   'performance_monitor': proof.get('performance_monitor', {}),
                   'policy': 'all installed selected-class PNG sheets; session-pinned across equipment, F10 and levels'}
        updated = copy.deepcopy(current); updated['version'] = version; updated['renderer_build_revision'] = receipt
        data = json.dumps(updated, indent=2).encode('utf-8'); manifest.write_bytes(data); mirror_manifest.write_bytes(data)
        shutil.copy2(validation, backup / 'validation.json')
        (backup / 'install-receipt.json').write_text(json.dumps(receipt, indent=2))
        print('Installed', version, 'with performance monitoring and session-resident player sheets; all art and CSV preserved')
    except BaseException:
        if replaced: shutil.copy2(old_binary, target)
        temporary.unlink(missing_ok=True); manifest.write_bytes(before); mirror_manifest.write_bytes(mirror_before)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['binary', 'game', 'manifest', 'mirror_manifest', 'backup', 'validation']: parser.add_argument(name, type=Path)
    args = parser.parse_args(); install(args.binary, args.game, args.manifest, args.mirror_manifest, args.backup, args.validation)
