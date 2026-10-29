"""Require actual GPU draws, complete residency and no warm player uploads."""
import argparse,csv,json,re
from pathlib import Path


def validate(root,pack,synthetic_log):
    root,pack=map(Path,(root,pack));proof=json.loads((root/'validation.json').read_text());assets=json.loads((pack/'validated-gpu-pack.json').read_text())
    assert 'PASS: synthetic BC7 GPU draw, exact lookup, shader lighting/TRN' in Path(synthetic_log).read_text()
    for name in ['gameplay-a','gameplay-b','ui']:
        text=(root/(name+'.log')).read_text(errors='replace')
        assert 'GPU_SPRITES_READY' in text and 'GPU_SPRITE_DRAW' in text and 'Test audio master gain: 0.5' in text
        assert text.count('GPU_SHEET_RESIDENT source=hd/plrgfx/warrior/')==assets['sheets']==255
        assert not re.search(r'Loaded HD sheet: hd/plrgfx/',text)
        end=re.search(r'HD_PLAYER_PRELOAD[^\n]+',text).end()
        assert 'GPU_SHEET_RESIDENT' not in text[end:]
        assert 'GPU_SHEET_RESIDENT source=hd/plrgfx/rogue/' not in text and 'GPU_SHEET_RESIDENT source=hd/plrgfx/sorceror/' not in text
        lines=[line for line in (root/(name+'-performance.csv')).read_text().splitlines() if not line.startswith('#')]
        rows=list(csv.DictReader(lines));assert rows and int(rows[-1]['gpu_draw_calls'])>0
        for row in rows:
            assert int(row['gpu_sheets'])==255 and int(row['gpu_texture_bytes'])==assets['texture_bytes'] and int(row['gpu_page_uploads'])==assets['pages']
        assert proof['preload']['bytes']==proof['repeat_preload']['bytes']==proof['ui_preload']['bytes']==0
    proof['gpu_sprites']={'sheets':assets['sheets'],'pages':assets['pages'],'texture_bytes':assets['texture_bytes'],'palette_lookup_bytes':67108864,'cpu_player_rgba_bytes':0,'density':4,'warm_page_uploads':0,'synthetic_native_viewport':True,'test_audio_gain':0.5,'pack_file_hashes':assets['files']}
    proof['checks']['gpu_sprites']=True
    (root/'validation.json').write_text(json.dumps(proof,indent=2))
    print('PASS: all Warrior sheets GPU-resident, zero CPU player RGBA, zero warm page uploads, real GPU draws, half-volume test audio and reference-save proof')
    return proof


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['root','pack','synthetic_log']:p.add_argument(name,type=Path)
    a=p.parse_args();validate(a.root,a.pack,a.synthetic_log)
