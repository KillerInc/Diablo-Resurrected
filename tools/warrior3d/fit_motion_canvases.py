"""Blender --python SCRIPT -- PLAN.json
Fit canvas/capture bounds to full motion. Never attenuate bones or shadows.
"""
import bpy,json,sys,math,gc
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from preflight_equipped_sets import check
from author_equipped_motion import author

def fit(file,author_models=False):
 file=Path(file);plan=json.loads(file.read_text());work=Path(plan['work']);checks=[];padding=[];authored=set()
 for j in plan['jobs']:
  model=Path(j['model'])
  if author_models and str(model) not in authored:
   motion=next(m for m in plan['motions'] if m['name']==j['motion'])
   if motion.get('recipe'):author(motion['recipe'],model)
   else:assert model.is_file(),model
   authored.add(str(model))
  rp=Path(j['reference']);ref=json.loads(rp.read_text());ref.update(canvas_logical=[512,512],canvas_anchor=[256,480],capture_bounds=True);rp.write_text(json.dumps(ref,indent=2));probe=check(model,rp);boxes=[b['bounds'] for b in probe['cell_bounds']];gx,gy=2048,3712;inv=plan['inventory'][j['code']][j['sheet']];base_w=inv['cell']//8
  original=inv.get('original_size',inv.get('size'));base_h=original[1]//ref['rows']//8
  x0=min(b[0] for b in boxes)-gx+base_w*4;x1=max(b[2] for b in boxes)-gx+base_w*4;y0=min(b[1] for b in boxes)-gy+(base_h-16)*8;y1=max(b[3] for b in boxes)-gy+(base_h-16)*8
  horizontal=max(0,math.ceil((16-x0)/8),math.ceil((x1+16-base_w*8)/8));top=max(0,math.ceil((16-y0)/8));bottom=max(0,math.ceil((y1+16-base_h*8)/8));canvas=[base_w+2*horizontal,base_h+top+bottom];anchor=[base_w//2+horizontal,base_h+top]
  # Enlarge raw capture too, keeping camera pixels/metre unchanged. The
  # projected world ground lies below the camera target by this fixed offset.
  art_scale=json.loads(Path(plan['calibration']).read_text())['global_pixel_scale'];raw_x=max(abs(b[k]-gx) for b in boxes for k in [0,2])/art_scale;camera_ground=.9*768/2.75*math.sqrt(.75);raw_y=max(abs(camera_ground+(b[k]-gy)/art_scale) for b in boxes for k in [1,3]);capture=64*math.ceil((2*max(raw_x,raw_y)+64)/64)
  ref.update(cell=max(ref.get('cell',768),capture),canvas_logical=canvas,canvas_anchor=anchor,pose_offsets=probe['pose_offsets']);ref.pop('capture_bounds',None);rp.write_text(json.dumps(ref,indent=2));inv.update(size=[canvas[0]*64,canvas[1]*8*ref['rows']],canvas_logical=canvas,canvas_anchor=anchor);result=check(model,rp);result['native_contact_warnings']=result['body_intersections'];result['safe']=result['minimum_body_margin']>3 and result['minimum_shadow_margin_before_blur']>7 and not result['native_contact_warnings'];result.update(sheet=j['sheet'],motion=j['motion'],pose_attenuation_applied=False);checks.append(result);(Path(j['root'])/'preflight.json').write_text(json.dumps(result,indent=2));(work/'preflight-progress.json').write_text(json.dumps(checks,indent=2));padding.append({'sheet':j['sheet'],'canvas':canvas,'anchor':anchor,'capture_pixels':ref['cell'],'native_contact_warnings':result['native_contact_warnings']});(work/'canvas-padding.json').write_text(json.dumps(padding,indent=2));file.write_text(json.dumps(plan,indent=2));print('FULL MOTION CHECK',j['sheet'],result['safe'],canvas,'contact warnings',len(result['native_contact_warnings']),flush=True);gc.collect()
 for c in plan.get('copies',[]):
  if c.get('source_sheet'):
   donor=c['source_sheet'];name=c['sheet'];plan['inventory'][name[:3]][name].update({k:v for k,v in plan['inventory'][donor[:3]][donor].items() if k in ['size','canvas_logical','canvas_anchor']})
 file.write_text(json.dumps(plan,indent=2));assert len(checks)==len(plan['jobs']) and all(r['safe'] for r in checks),'Full-motion capture needs review';print('All full-motion canvases fitted without pose changes',flush=True)
if __name__=='__main__':fit(sys.argv[sys.argv.index('--')+1])
