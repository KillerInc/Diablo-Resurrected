"""Build a root-anchored HD canvas, without installing it.

python SCRIPT BODY_FRAMES OVERSCAN_SHADOWS RENDER.json CALIBRATION.json OUTPUT
Raw bodies are 768/1024 square; shadows have 256 extra pixels on every side.
Uniform art scale is retained; the projected world ground origin anchors to the
center of a 64x32 logical tile. Optional canvas_logical/canvas_anchor metadata
selects original cell sizes; the default is the 0.4.1 expanded 192-pixel canvas.
"""
import hashlib,json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

body_root,shadow_root,render_file,calibration,out=map(Path,sys.argv[1:6]);out.mkdir(parents=True,exist_ok=True)
info=json.loads(render_file.read_text());cal=json.loads(calibration.read_text())
scale=cal['global_pixel_scale'];origin=info['ground_origin_pixel']
preview_prefix=info.get('preview_prefix','knee-centered')
density=8;canvas_logical=info.get('canvas_logical',192)
logical_width,logical_height=(canvas_logical,canvas_logical) if isinstance(canvas_logical,int) else canvas_logical
cell=logical_width*density;cell_height=logical_height*density;rows=info['output_rows'];filename=info.get('sheet','wlnat.png');anchor=tuple(info.get('canvas_anchor',[96,160]));ground=(anchor[0]*density,(anchor[1]-16)*density)
assert 0<=anchor[0]<=logical_width and 0<=anchor[1]<=logical_height
raw_cell=Image.open(body_root/'body-0-0.png').width
dx=ground[0]-scale*origin[0];dy=ground[1]-scale*origin[1]
sheet=Image.new('RGBA',(cell*8,cell_height*rows));preview=[];report={
    'global_pixel_scale':scale,'canvas_logical':[logical_width,logical_height],'density':density,
    'anchor':list(anchor),'ground_origin_pixel':list(ground),
    'fixed_registration_all_directions':[dx,dy],'body_cells':[],'shadow_cells':[],
    'sun_position':info['sun_position'],'model_geometry_rescaled':False,
    'frame_count':rows,'direction_count':8}
for row in range(rows):
    source_row=info.get('source_render_rows',list(range(rows)))[row]
    screen_offset=(info.get('pose_image_offsets') or [[0,0]]*rows)[row]
    frame_dx=dx+screen_offset[0];frame_dy=dy+screen_offset[1]
    cells=[]
    for direction in range(8):
        body=Image.open(body_root/f'body-{direction}-{source_row}.png').convert('RGBA');assert body.size==(raw_cell,raw_cell)
        body=body.transform((cell,cell_height),Image.Transform.AFFINE,(1/scale,0,-frame_dx/scale,0,1/scale,-frame_dy/scale),resample=Image.Resampling.BICUBIC)
        rgba=np.array(body);rgb=rgba[:,:,:3].astype(np.float32);lum=rgb@np.array([.2126,.7152,.0722],dtype=np.float32)
        graded=(lum[:,:,None]+.86*(rgb-lum[:,:,None]))*.62
        if info.get('fire_effect'):
            masks=list((body_root/'fire-masks'/f'{direction}-{source_row}').rglob('*.png'));assert len(masks)==1,('Missing fire emission mask',direction,source_row)
            mask=Image.open(masks[0]).convert('L').transform((cell,cell_height),Image.Transform.AFFINE,(1/scale,0,-frame_dx/scale,0,1/scale,-frame_dy/scale),resample=Image.Resampling.BICUBIC)
            mix=np.clip(np.asarray(mask,dtype=np.float32)[:,:,None]/255*2,0,1)
            if info['fire_effect'].get('style')=='lightning':fire_rgb=rgb*np.array([.85,.92,1.10],dtype=np.float32)
            else:
                fire_rgb=rgb*np.array([1,1.08,.25],dtype=np.float32);fire_rgb[:,:,1]=np.minimum(fire_rgb[:,:,1],fire_rgb[:,:,0])
            graded=graded*(1-mix)+fire_rgb*mix
        rgba[:,:,:3]=np.clip(graded,0,255).astype(np.uint8);body=Image.fromarray(rgba)
        shadow=Image.open(shadow_root/f'shadow-{direction}-{source_row}.png');assert shadow.size==(raw_cell+512,raw_cell+512)
        alpha=shadow.getchannel('A').transform((cell,cell_height),Image.Transform.AFFINE,(1/scale,0,-frame_dx/scale+256,0,1/scale,-frame_dy/scale+256),resample=Image.Resampling.BICUBIC)
        alpha=alpha.filter(ImageFilter.GaussianBlur(2)).point(lambda x:round(x*.7))
        for name,box in [('body_cells',body.getbbox()),('shadow_cells',alpha.getbbox())]:
            assert box and min(box[:2])>0 and box[2]<cell and box[3]<cell_height,('clipped',name,row,direction,box)
            report[name].append({'row':row,'direction':direction,'bounds':box})
        ground_shadow=Image.new('RGBA',(cell,cell_height));ground_shadow.putalpha(alpha)
        composed=Image.alpha_composite(ground_shadow,body);sheet.paste(composed,(direction*cell,row*cell_height));cells.append(composed)
    canvas=Image.new('RGB',(1152,420),(38,38,38));draw=ImageDraw.Draw(canvas)
    for column,direction in enumerate([0,2,3]):
        view=Image.new('RGBA',(cell,cell_height),(46,46,46,255));view=Image.alpha_composite(view,cells[direction]);vd=ImageDraw.Draw(view)
        if info.get('preview_anchor',True):
            gx,gy=ground;vd.line([(gx-256,gy),(gx,gy-128),(gx+256,gy),(gx,gy+128),(gx-256,gy)],fill=(80,125,100,255),width=3)
            vd.line([(gx-24,gy),(gx+24,gy)],fill=(60,255,130,255),width=4);vd.line([(gx,gy-24),(gx,gy+24)],fill=(60,255,130,255),width=4)
        fit=min(384/cell,384/cell_height);view=view.resize((round(cell*fit),round(cell_height*fit)),Image.Resampling.LANCZOS)
        canvas.paste(view.convert('RGB'),(column*384+(384-view.width)//2,24+(384-view.height)//2));draw.text((column*384+10,7),['South','West','Northwest'][column],fill='white')
    draw.text((10,409),info.get('preview_caption','Green cross: fixed tile ground origin. Full moving shadow, sun southeast.'),fill='white');preview.append(canvas)
    if row==info.get('preview_contact_row',8):canvas.save(out/(preview_prefix+'-contact.png'))
dest=out/filename;sheet.save(dest,compress_level=6)
(out/(filename+'.layout')).write_text(f'D1R_SHEET_V1 {density} {anchor[0]} {anchor[1]}\n',encoding='ascii')
report['size']=[cell*8,cell_height*rows];report['sheet_sha256']=hashlib.sha256(dest.read_bytes()).hexdigest();report['pose_image_offsets']=info.get('pose_image_offsets',[])
(out/'validation.json').write_text(json.dumps(report,indent=2))
duration=200 if Path(filename).stem.endswith(('as','st')) else (100 if Path(filename).stem.endswith('dt') else 50)
preview[0].save(out/(preview_prefix+'-preview.gif'),save_all=True,append_images=preview[1:],duration=duration,loop=0,optimize=False)
print('Validated',rows*8,'body and shadow cells; fixed root anchor, unchanged art scale:',dest)
