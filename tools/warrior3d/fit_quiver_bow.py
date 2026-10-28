"""Blender --python SCRIPT -- QUIVER_PLAN.json
Check existing approved poses and enlarge canvases only when needed.
No pose, scale, shadow or sheet-size attenuation.
"""
import sys,json,math,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));from preflight_equipped_sets import check
plan_file=Path(sys.argv[sys.argv.index('--')+1]);w=plan_file.resolve().parent;p=json.loads(plan_file.read_text());checks=[]
for j in p['jobs']:
 model=Path(j['model'])
 if True:
  rp=Path(j['reference']);r=json.loads(rp.read_text());r['capture_bounds']=True;rp.write_text(json.dumps(r));result=check(model,rp);boxes=[b['bounds'] for b in result['cell_bounds']];cw,ch=r['canvas_logical'] if isinstance(r['canvas_logical'],list) else [r['canvas_logical']]*2
  left=max(0,math.ceil((16-min(b[0] for b in boxes))/8));right=max(0,math.ceil((max(b[2] for b in boxes)+16-cw*8)/8));top=max(0,math.ceil((16-min(b[1] for b in boxes))/8));bottom=max(0,math.ceil((max(b[3] for b in boxes)+16-ch*8)/8));pad=max(left,right);r['canvas_logical']=[cw+2*pad,ch+top+bottom];r['canvas_anchor']=[r['canvas_anchor'][0]+pad,r['canvas_anchor'][1]+top];r.pop('capture_bounds');rp.write_text(json.dumps(r,indent=2));result=check(model,rp);result.update(sheet=j['sheet'],motion=j['motion']);checks.append(result);(Path(j['root'])/'preflight.json').write_text(json.dumps(result,indent=2));p['inventory']['wlb'][j['sheet']].update(canvas_logical=r['canvas_logical'],canvas_anchor=r['canvas_anchor']);p['inventory']['wlb'][j['sheet']]['size']=[r['canvas_logical'][0]*64,r['canvas_logical'][1]*8*j.get('output_rows',r['rows'])];(w/'preflight-progress.json').write_text(json.dumps(checks,indent=2));print(j['sheet'],result['safe'],r['canvas_logical'],flush=True)

(w/'plan.json').write_text(json.dumps(p,indent=2));assert all(c['safe'] for c in checks)
