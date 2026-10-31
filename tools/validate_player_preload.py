"""Validate isolated player-preload gameplay/UI logs without uploading artwork."""
import argparse
import json
from pathlib import Path
import re
from install_layout_table import sha

PATTERN = re.compile(r'HD_PLAYER_PRELOAD class=(\S+) loaded=(\d+) skipped=(\d+) resident=(\d+) bytes=(\d+) workers=(\d+) elapsed_ms=(\d+)')


def check_case(root, name, player_class, expected, compare):
    text = (root / (name + '.log')).read_text(errors='replace')
    matches = list(PATTERN.finditer(text)); assert len(matches) == 1, (name, 'expected one preload')
    match = matches[0]; cls, loaded, skipped, resident, size, workers, elapsed = match.groups()
    assert cls == player_class and int(loaded) == int(resident) == expected and int(skipped) == 0
    assert text[match.end():].count('Loaded HD sheet: hd/plrgfx/' + player_class + '/') == 0, (name, 'player sheet reloaded')
    assert text[match.end():].count('GPU_SHEET_RESIDENT source=hd/plrgfx/' + player_class + '/') == 0, (name, 'warm GPU upload')
    assert not re.search(r'Loaded HD sheet: hd/plrgfx/(?!' + re.escape(player_class) + r'/)', text)
    assert text.count('Loaded HD sheet: hd/plrgfx/' + player_class + '/') + text.count('GPU_SHEET_RESIDENT source=hd/plrgfx/' + player_class + '/') == expected
    if compare: assert 'Same outcome as initial run' in text and 'Different outcome' not in text
    process = json.loads((root / (name + '-process.json')).read_text(encoding='utf-8-sig')); assert process['exit'] == 0
    diagnostics = (root / (name + '-stderr.log')).read_text(errors='replace')
    tables=diagnostics.count('HD_LAYOUT_CSV: loaded rows=')
    # Isolated GPU packs and base PNGs can be separate mounted providers;
    # each provider's immutable table is exercised by the provider unit tests.
    assert tables in ((1,2) if 'GPU_SHEET_RESIDENT' in text else (1,))
    return {'class': cls, 'loaded': int(loaded), 'skipped': int(skipped), 'resident': int(resident), 'bytes': int(size),
            'workers': int(workers), 'elapsed_ms': int(elapsed), 'peak_private_bytes_sampled': process['peak_private_bytes'], 'exit': process['exit']}


def validate(root, hd, player_class, provider_log, integration_log):
    root, hd = Path(root), Path(hd)
    count = len(list((hd / 'plrgfx' / player_class).rglob('*.png'))); assert count > 0
    a = check_case(root, 'gameplay-a', player_class, count, True)
    b = check_case(root, 'gameplay-b', player_class, count, True)
    ui = check_case(root, 'ui', player_class, count, False)
    ui_text = (root / 'ui.log').read_text(errors='replace'); assert 'Renderer mode: HD' in ui_text and 'Renderer mode: Classic' in ui_text
    assert a['bytes'] == b['bytes'] == ui['bytes']
    assert re.search(r'100% tests passed, 0 tests failed out of [456]', Path(provider_log).read_text(errors='replace'))
    assert 'PASS: provenance' in Path(integration_log).read_text(errors='replace')
    proof = {'version': (Path(__file__).resolve().parents[1] / 'REINCARNATED_VERSION').read_text().strip(),
             'executable_sha256': sha(root / 'package/Diablo Reincarnated.exe'), 'class_png_count': count,
             'preload': a, 'repeat_preload': b, 'ui_preload': ui,
             'checks': {'provider_tests': True, 'integration': True, 'gameplay_reference_same': True,
                        'gameplay_reference_repeat_same': True, 'warm_player_reloads': 0, 'other_class_preloads': 0, 'ui_exit': 0}}
    (root / 'validation.json').write_text(json.dumps(proof, indent=2))
    print('Validated two matching gameplay replays and UI/F10; resident sheets:', count, 'bytes:', a['bytes'], 'preload seconds:', a['elapsed_ms']/1000)
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['root', 'hd', 'player_class', 'provider_log', 'integration_log']: parser.add_argument(name)
    args = parser.parse_args(); validate(args.root, args.hd, args.player_class, args.provider_log, args.integration_log)
