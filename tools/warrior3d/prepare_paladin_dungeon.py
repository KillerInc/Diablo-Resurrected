"""Reuse approved local walk/idle renders in the original dungeon sheet layouts.

python prepare_paladin_dungeon.py WORKSPACE ORIGINAL_NN8 EXTRACTED_CL2 OUTPUT
Does not install assets. Dungeon idle is a neutral placeholder, not a combat pose.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys

workspace, originals, cl2, output = map(Path, sys.argv[1:5])
tools = Path(__file__).resolve().parent
calibration = workspace/'paladin-town-walk/output/validation.json'
for sheet, source, indices in [
    ('wlnaw', workspace/'paladin-short-stride-final', list(range(8))),
    ('wlnas', workspace/'paladin-town-idle', list(range(0,20,2))),
]:
    target = output/sheet
    reference = target/'reference'
    subprocess.run([sys.executable, str(tools/'prepare_town_walk.py'),
                    str(originals/(sheet+'.png')), str(cl2/(sheet+'.cl2')),
                    str(reference)], check=True)
    ref = json.loads((reference/'reference.json').read_text())
    assert ref['rows'] == len(indices)
    shadow_source = source/('shadows' if sheet=='wlnaw' else 'projected-shadows')
    for kind, source_dir in [('body',source/'frames'), ('shadow',shadow_source)]:
        dest = target/('frames' if kind=='body' else 'shadows')
        dest.mkdir(parents=True, exist_ok=True)
        for d in range(8):
            for r, original_row in enumerate(indices):
                shutil.copyfile(source_dir/f'{kind}-{d}-{original_row}.png', dest/f'{kind}-{d}-{r}.png')
    subprocess.run([sys.executable, str(tools/'assemble_paladin_town_walk.py'),
                    str(target/'frames'), str(reference), str(target/'output'),
                    str(calibration), str(target/'shadows')], check=True)
    (target/'sampling.json').write_text(json.dumps({
        'source': str(source), 'source_render_rows': indices,
        'sheet': sheet, 'neutral_idle_placeholder': sheet=='wlnas',
        'engine_changes': False,
    }, indent=2))
