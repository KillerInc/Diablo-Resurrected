"""Combine existing approved bodies with player-rule ground shadows, privately.

python assemble_npc_shadows.py recipes.json renders installed-HD output-HD
Recipes list exact native source samples, body paths and fixed registration.
Never recolour, resize, recenter or change the frame count of the actor.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

def assemble(spec, renders, installed, output):
    width, height = spec['cell']
    count = len(spec['times'])
    old = Image.open(installed/spec['rel']).convert('RGBA')
    assert old.size == (width, height*count), (spec['name'], old.size)
    sheet = Image.new('RGBA', old.size)
    audit = []
    for row, source in enumerate(spec['body_frames']):
        body = Image.open(Path(spec['body'])/f"body-{source:0{spec['body_digits']}d}.png").convert('RGBA')
        assert body.size == (width, height)
        raw = Image.open(renders/spec['name']/f'shadow-{row:02}.png').getchannel('A')
        # Player shadows are softened by 2 pixels at authoring density 8, then
        # compiled at density 4. Use the equivalent one-pixel 4x blur here.
        alpha = raw.filter(ImageFilter.GaussianBlur(1)).point(lambda a: round(a*.7))
        shadow = Image.new('RGBA', body.size)
        shadow.putalpha(alpha)
        merged = Image.alpha_composite(shadow, body)
        registered = Image.new('RGBA', body.size)
        registered.paste(merged, spec['registration'])
        registered_body = Image.new('RGBA', body.size)
        registered_body.paste(body, spec['registration'])
        previous = np.asarray(old.crop((0,row*height,width,(row+1)*height)))
        original = np.asarray(registered_body)
        opaque = original[:,:,3] == 255
        assert np.array_equal(previous[opaque], original[opaque]), (spec['name'], row, 'approved body differs')
        box = registered.getbbox()
        assert box and box[0]>0 and box[1]>0 and box[2]<width and box[3]<height, (spec['name'],row,'clipped shadow',box)
        shadow_box = alpha.getbbox()
        assert shadow_box and shadow_box[0]>0 and shadow_box[1]>0 and shadow_box[2]<width and shadow_box[3]<height, (spec['name'],row,'raw shadow clipped',shadow_box)
        assert alpha.getextrema()[1] <= 179
        sheet.paste(registered, (0,row*height))
        audit.append({'frame':row,'source_frame':spec['times'][row],
                      'bounds':box,'shadow_bounds':shadow_box,'opaque_body_unchanged':True})
    destination = output/spec['rel']
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination)
    return {'name':spec['name'],'path':spec['rel'],'frames':count,'cells':audit,
            'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('recipes','renders','installed','output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    results = [assemble(s,args.renders,args.installed,args.output)
               for s in json.loads(args.recipes.read_text())]
    (args.output.parent/'shadow-audit.json').write_text(json.dumps(results,indent=2))
    print('Validated shadows and unchanged opaque bodies:', len(results), 'NPCs')
