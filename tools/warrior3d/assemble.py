"""Assemble Blender renders into vanilla-compatible eight-direction sheets."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--reference',type=Path)
    parser.add_argument('--preview-only',action='store_true')
    args=parser.parse_args()
    manifest=json.loads((args.model/'model-manifest.json').read_text())
    cell=manifest['resolution']
    report={'cell':[cell,cell],'columns':8,'animations':{},'installed':False,'status':'prototype; fidelity not approved'}
    reference=json.loads(args.reference.read_text()) if args.reference else None
    contact=Image.new('RGBA',(cell*4,cell*2),(28,29,34,255))
    direction_names=['S','SW','W','NW','N','NE','E','SE']
    for direction in range(8):
        frame=Image.open(args.model/'frames/idle'/f'{direction}_00.png').convert('RGBA')
        contact.alpha_composite(frame,((direction%4)*cell,(direction//4)*cell))
    draw=ImageDraw.Draw(contact)
    for direction,name in enumerate(direction_names):
        draw.text(((direction%4)*cell+20,(direction//4)*cell+20),name,fill=(235,220,190,255),stroke_width=1)
    contact.save(args.model/'eight-directions.png')
    if args.preview_only:
        print(f'Saved {args.model/"eight-directions.png"}')
        return
    for name,count in manifest['actions'].items():
        sheet=Image.new('RGBA',(cell*8,cell*count),(0,0,0,0))
        boxes=[]; clipped=[]; scores=[]
        masks=json.loads((args.reference.parent/f'{name}-masks.json').read_text()) if args.reference else None
        for frame_index in range(count):
            row=[]
            for direction in range(8):
                filename=args.model/f'frames/{name}/{direction}_{frame_index:02d}.png'
                with Image.open(filename) as source:
                    if source.size!=(cell,cell) or source.mode!='RGBA':
                        raise ValueError(f'{filename}: wrong dimensions or no alpha')
                    frame=source.copy()
                bounds=frame.getchannel('A').getbbox()
                if bounds is None: raise ValueError(f'{filename}: empty frame')
                if bounds[0]==0 or bounds[1]==0 or bounds[2]==cell or bounds[3]==cell:
                    clipped.append([direction,frame_index])
                row.append(bounds)
                sheet.paste(frame,(direction*cell,frame_index*cell))
                if masks is not None:
                    actual=frame.getchannel('A').resize((96,96),Image.Resampling.BOX)
                    a=[v>=128 for v in actual.tobytes()]
                    b=[v>=128 for v in masks[frame_index*8+direction]]
                    union=sum(x or y for x,y in zip(a,b)); intersection=sum(x and y for x,y in zip(a,b))
                    scores.append(intersection/union if union else 0)
            boxes.append(row)
        if clipped: raise ValueError(f'{name}: clipped frames {clipped}')
        basename='wlnas.png' if name=='idle' else 'wlnaw.png'
        destination=args.model/'export/hd/plrgfx/warrior/wln'/basename
        destination.parent.mkdir(parents=True,exist_ok=True)
        sheet.save(destination,compress_level=6)
        expected=(cell*8,cell*count)
        if reference and list(expected)!=reference['animations'][name]['source_size']:
            raise ValueError('Sheet dimensions differ from original NN8 layout')
        report['animations'][name]={'frames':count,'cells':count*8,'size':expected,'bounds':boxes,
            'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
            'mean_reference_silhouette_iou':sum(scores)/len(scores) if scores else None,
            'minimum_reference_silhouette_iou':min(scores) if scores else None}
        if reference:
            report['animations'][name]['reference_sha256']=reference['animations'][name]['source_sha256']
        # Offline animation preview at South-facing direction 0; original pixels are not copied.
        previews=[]
        for index in range(count):
            image=Image.open(args.model/f'frames/{name}/0_{index:02d}.png').convert('RGBA')
            image.thumbnail((384,384))
            bg=Image.new('RGBA',image.size,(28,29,34,255)); bg.alpha_composite(image)
            previews.append(bg.convert('RGB'))
        previews[0].save(args.model/f'{name}-preview.gif',save_all=True,append_images=previews[1:],duration=100,loop=0)
    (args.model/'export-validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({name:{k:v for k,v in result.items() if k!='bounds'} for name,result in report['animations'].items()},indent=2))


if __name__=='__main__':
    main()
