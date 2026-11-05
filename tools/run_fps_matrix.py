"""Run isolated, silent, sequential rendering comparisons from a copied save."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess


def rows(path):
    return list(csv.DictReader(io.StringIO('\n'.join(
        line for line in path.read_text().splitlines() if not line.startswith('#')))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('fixture', type=Path, help='Copied full-game slot 1 save, config, stash and demo_7.dmo')
    parser.add_argument('output', type=Path, help='New private directory; never put saves in Git')
    parser.add_argument('--data-dir', type=Path, default=Path('D:/Games/Diablo'))
    parser.add_argument('--cases', nargs='+', default=['baseline-a', 'classic', 'flat-light', 'no-gpu-actors', 'unzoomed', '720p', 'baseline-b'])
    args = parser.parse_args()
    executable, fixture, output = args.executable.resolve(), args.fixture.resolve(), args.output.resolve()
    assert executable.is_file() and not output.exists(), 'Use a built executable and a new output directory'
    configs = {
        'baseline-a': {}, 'baseline-b': {},
        'classic': {'HD Graphics': '0'},
        'flat-light': {'Per-pixel Lighting': '0'},
        'no-gpu-actors': {}, 'unzoomed': {'Zoom': '0'},
        '720p': {'Width': '1280', 'Height': '720'},
    }
    assert all(case in configs for case in args.cases)
    required = ['single_1.sv', 'stash.sv', 'diablo.ini', 'demo_7.dmo']
    assert all((fixture / name).is_file() for name in required)
    output.mkdir(parents=True)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    inputs = {name: digest(fixture / name) for name in required}
    report = {'executable_sha256': digest(executable), 'fixture_sha256': inputs, 'cases': {}}
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    runner = Path(__file__).with_name('run_sprite_perf_probe.ps1').resolve()
    shell = shutil.which('pwsh')
    assert shell, 'PowerShell 7 is required by the replay runner'
    for case in args.cases:
        destination = output / case
        destination.mkdir()
        for name in required:
            shutil.copy2(fixture / name, destination / name)
        changes = {'HD Graphics': '1', 'Zoom': '1', 'Per-pixel Lighting': '1', **configs[case]}
        ini = (destination / 'diablo.ini').read_text(encoding='utf-8-sig')
        section = re.search(r'(?ms)^\[Graphics\]\n(.*?)(?=^\[|\Z)', ini)
        assert section, 'Missing Graphics section'
        body = section.group(1)
        for key, value in changes.items():
            body, count = re.subn(r'(?m)^' + re.escape(key) + r'=[^\r\n]*', key + '=' + value, body)
            assert count == 1, key
        ini = ini[:section.start(1)] + body + ini[section.end(1):]
        (destination / 'diablo.ini').write_text(ini, encoding='utf-8')
        if case == '720p':
            demo = bytearray((destination / 'demo_7.dmo').read_bytes())
            assert demo[0] == 3
            struct.pack_into('<HH', demo, 5, 1280, 720)
            (destination / 'demo_7.dmo').write_bytes(demo)
        env = os.environ.copy()
        env.pop('D1R_DISABLE_GPU_SPRITES', None)
        if case == 'no-gpu-actors':
            env['D1R_DISABLE_GPU_SPRITES'] = '1'
        env['D1R_CPU_PROFILE_LOG'] = str(output / (case + '-cpu.csv'))
        command = [shell, '-NoProfile', '-File', str(runner), '-Root', str(output),
                   '-Case', case, '-Executable', str(executable), '-DataDirectory', str(args.data_dir), '-Profile']
        with (output / (case + '-runner.log')).open('w') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                           startupinfo=startup, check=True, timeout=1000)
        process = json.loads((output / (case + '-process.json')).read_text())
        assert process['exit'] == 0 and process['executable_sha256'].lower() == report['executable_sha256']
        text = (output / (case + '.log')).read_text(errors='replace')
        assert 'Test display: left secondary' in text and 'Test audio master gain: 0.5' in text
        expected_mode = 'Classic' if case == 'classic' else 'HD'
        assert 'Initial renderer mode: ' + expected_mode in text
        samples = rows(output / (case + '-performance.csv'))[-8:]
        assert len(samples) >= 3, 'Insufficient warm intervals'
        assert all(row['mode'] == expected_mode for row in samples)
        assert all((int(row['gpu_draw_calls']) == 0) == (case in ('classic', 'no-gpu-actors')) for row in samples)
        frames = sum(int(row['frames']) for row in samples)
        result = {key: sum(float(row[key]) * int(row['frames']) for row in samples) / frames
                  for key in ['avg_ms', 'draw_cpu_ms', 'compose_cpu_ms', 'present_cpu_ms']}
        result.update(fps=1000 / result['avg_ms'], frames=frames, settings=changes)
        assert all(int(row['sheet_bytes']) == int(row['decodes']) == int(row['failures']) == 0 for row in samples)
        stages = {}
        for row in rows(output / (case + '-cpu.csv')):
            if float(row['seconds']) < float(samples[0]['seconds']):
                continue
            item = stages.setdefault(row['stage'], {'ms': 0, 'frames': 0})
            item['ms'] += float(row['total_cpu_ms'])
            item['frames'] += int(row['frames'])
        assert stages and all(item['frames'] > 0 for item in stages.values())
        result['stage_ms'] = {key: item['ms'] / item['frames'] for key, item in stages.items()}
        report['cases'][case] = result
        assert all(digest(fixture / name) == value for name, value in inputs.items())
        (output / 'results.json').write_text(json.dumps(report, indent=2))
        print(f"{case}: {result['fps']:.1f} FPS, {result['avg_ms']:.2f} ms", flush=True)


if __name__ == '__main__':
    main()
