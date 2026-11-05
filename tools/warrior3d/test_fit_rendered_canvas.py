"""Synthetic check that canvas padding preserves pixels per metre and tile registration."""
import json,tempfile,unittest,subprocess,sys
from pathlib import Path
from PIL import Image,ImageDraw
from fit_rendered_canvas import fit

class CanvasTests(unittest.TestCase):
 def test_clipped_cells_gain_padding_without_moving_world_anchor(self):
  with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
   root=Path(tmp);frames=root/'frames';shadows=root/'shadows';frames.mkdir();shadows.mkdir()
   for d in range(8):
    body=Image.new('RGBA',(256,256));ImageDraw.Draw(body).rectangle((5,5,249,249),fill=(100,50,30,255));body.save(frames/f'body-{d}-0.png')
    shadow=Image.new('RGBA',(768,768));ImageDraw.Draw(shadow).rectangle((261,261,505,505),fill=(0,0,0,255));shadow.save(shadows/f'shadow-{d}-0.png')
   info={'canvas_logical':[32,32],'canvas_anchor':[16,32],'ground_origin_pixel':[200,200],'output_rows':1,'sheet':'synthetic.png','sun_position':[3,-4,6]};render=frames/'render.json';reference=root/'reference.json';cal=root/'cal.json'
   for p,data in [(render,info),(reference,info),(cal,{'global_pixel_scale':1})]:p.write_text(json.dumps(data))
   change=fit(frames,shadows,render,cal,reference);self.assertEqual(change['padding_logical'],[11,11,0,0]);new=json.loads(render.read_text());self.assertEqual(new['canvas_anchor'],[27,43]);self.assertEqual(new['ground_origin_pixel'],[200,200])
   result=subprocess.run([sys.executable,str(Path(__file__).with_name('assemble_paladin_canvas.py')),str(frames),str(shadows),str(render),str(cal),str(root/'output')],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   proof=json.loads((root/'output/validation.json').read_text());self.assertEqual(proof['global_pixel_scale'],1);self.assertEqual(proof['frame_count'],1);self.assertEqual(len(proof['body_cells']),8)
   # Original top-left relative to the tile stays at -195 pixels on both axes.
   for box in proof['body_cells']:self.assertEqual(box['bounds'][0]-proof['ground_origin_pixel'][0],5-200);self.assertEqual(box['bounds'][1]-proof['ground_origin_pixel'][1],5-200)
if __name__=='__main__':unittest.main()
