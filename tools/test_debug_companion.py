"""Exercise the compiled Lua developer console using an isolated replay fixture."""
import argparse
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('root', type=Path, help='Private replay root with console/diablo.ini and demo_1.dmo')
    parser.add_argument('--data-dir', type=Path, default=Path('D:/Games/Diablo'))
    args = parser.parse_args()
    executable, root = args.executable.resolve(), args.root.resolve()
    assert (executable.parent / 'd1reincarnated.mpq').is_file(), 'Copy the existing support archive beside the test executable'
    save = root / 'console'
    # Reuse the established isolated-config muting implementation.
    subprocess.run(['powershell', '-NoProfile', '-File', str(Path(__file__).with_name('run_gpu_replay.ps1')),
                    '-Root', str(root), '-Case', 'console', '-ConfigureOnly'], check=True)
    command = ("local d=require('devilutionx.dev'); "
               "assert(type(d.player.gold.give)=='function'); "
               "assert(d.player.god(true)=='God mode: On'); "
               "assert(d.player.god(false)=='God mode: Off'); "
               "require('devilutionx.log').info('D1R_DEBUG_CONSOLE_OK')")
    log = root / 'console.log'
    log.unlink(missing_ok=True)
    env = os.environ.copy()
    env.update(D1R_TEST_AUDIO_GAIN='0.5', D1R_TRACE_PLAYER_SHEETS='1',
               D1R_PERF_LOG=str(root / 'console-performance.csv'))
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    with (root / 'console-stdout.log').open('w') as out, (root / 'console-stderr.log').open('w') as err:
        result = subprocess.run([str(executable), '--spawn', '--diablo', '--demo', '1', '--timedemo',
                                 '--save-dir', str(save), '--config-dir', str(save),
                                 '--data-dir', str(args.data_dir), '--verbose', '--log-to-file', str(log),
                                 '-n', '+' + command], cwd=executable.parent, env=env,
                                stdout=out, stderr=err, startupinfo=startup, timeout=360)
    assert result.returncode == 0, f'Debug console replay exited {result.returncode}'
    text = log.read_text(errors='replace')
    assert 'D1R_DEBUG_CONSOLE_OK' in text, 'Developer-console command did not complete'
    assert 'GPU_SPRITE_DRAW' in text, 'Missing actual HD GPU draw'
    assert text.count('GPU_SHEET_RESIDENT source=hd/plrgfx/warrior/') == 255
    print('PASS: developer Lua module, reversible god-mode toggle, gold API and 255-sheet HD GPU rendering')


if __name__ == '__main__':
    main()
