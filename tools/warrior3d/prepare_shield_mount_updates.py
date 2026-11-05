"""Prepare a private shield-only correction plan using existing body animations.

python SCRIPT OLD_PLAN NEW_WORK NATIVE_SWORD_PLAN SHIELD_BASH_PLAN IDLE_MODEL IDLE_REFERENCE
The combined idle is sampled exactly; no body poses are changed.
"""
import copy,json,sys,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));from shield_mount import correct
old_plan,output,sword_plan,bash_plan,idle_model,idle_reference=map(Path,sys.argv[1:]);base=old_plan.parent
old=json.loads(old_plan.read_text());work=output.resolve();work.mkdir(exist_ok=False);plan=copy.deepcopy(old);manifest=json.loads((Path(old['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text());plan.update(work=str(work),starting_custom_manifest=manifest,jobs=[],motions=[],copies=[],shield_grip_correction=True)
for j in old['jobs']:
 if j['code']=='wls':continue
 if j['sheet']=='wldat':j=next(x for x in json.loads((sword_plan).read_text())['jobs'] if x['sheet']=='wldat')
 if j['sheet']=='wluat':j=json.loads((bash_plan).read_text())['jobs'][0]
 j=copy.deepcopy(j);r=json.loads(Path(j['reference']).read_text());r['equipment']=[correct(e) for e in r['equipment']];r['preview_caption']=j['sheet'].upper()+' | corrected small handgrip / elbow strap';root=work/'jobs'/j['sheet'];root.mkdir(parents=True,exist_ok=True);ref=root/'reference.json';ref.write_text(json.dumps(r,indent=2));j.update(root=str(root),reference=str(ref),motion=j['sheet']);plan['jobs'].append(j)
# The previously copied combined idle must also be rerendered.
r=json.loads((idle_reference).read_text());r.pop('bounds',None);r['equipment']=[correct(e) for e in r['equipment']];r['source_frames']=list(range(10));r['preview_prefix']='wldas';root=work/'jobs/wldas';root.mkdir(parents=True,exist_ok=True);ref=root/'reference.json';ref.write_text(json.dumps(r,indent=2));models=work/'models';models.mkdir(exist_ok=True);recipe={'source':str(idle_model),'frames':list(range(0,160,16)),'name':'unchanged combined idle samples','arms':[]};rp=models/'wldas.json';rp.write_text(json.dumps(recipe,indent=2));model=models/'wldas.glb';plan['jobs'].insert(0,{'sheet':'wldas','code':'wld','action':'as','model':str(model),'motion':'wldas','root':str(root),'reference':str(ref)});plan['author_once']={'recipe':str(rp),'model':str(model)}
for c in old['copies']:
 if c['sheet'].startswith('wls') or c['sheet']=='wldas':continue
 plan['copies'].append(copy.deepcopy(c))
for name,rec in manifest['sheets'].items():
 if name.startswith('wls'):
  plan['copies'].append({'sheet':name,'path':rec['source']});v=plan['inventory']['wls'][name];v.update(size=rec['size'],canvas_anchor=list(map(int,rec['layout'].split()[2:4])),canvas_logical=[rec['size'][0]//64,rec['size'][1]//(8*v['rows'])])
for j in plan['jobs']:
 r=json.loads(Path(j['reference']).read_text());v=plan['inventory'][j['code']][j['sheet']];logical=r['canvas_logical'];dims=[logical,logical] if isinstance(logical,int) else logical;v.update(size=[dims[0]*64,dims[1]*8*r['rows']],canvas_anchor=r['canvas_anchor'])
for j in plan['jobs']:
 if j['sheet'] not in ['wldaw','wluaw','wldbl']:continue
 f=Path(j['reference']);r=json.loads(f.read_text());r.update(canvas_logical=[98,96],canvas_anchor=[49,96]);f.write_text(json.dumps(r,indent=2));plan['inventory'][j['code']][j['sheet']].update(size=[6272,96*8*r['rows']],canvas_logical=[98,96],canvas_anchor=[49,96])
for name in ['wldwl','wluwl']:plan['inventory'][name[:3]][name].update(size=[6272,96*8*plan['inventory'][name[:3]][name]['rows']],canvas_logical=[98,96],canvas_anchor=[49,96])
plan['shadow_border']={'sheets':['wldaw','wluaw','wldwl','wluwl','wldbl'],'logical_pixels_each_side':1,'character_scale_and_world_anchor_preserved':True}
plan['motions']=[{'name':j['motion']} for j in plan['jobs']];plan['starting_game_hashes']={n:rec['sha256'] for n,rec in manifest['sheets'].items() if n.startswith(('wld','wls','wlu'))};(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Plan',len(plan['jobs']),'shield render jobs',len(plan['copies']),'copies; total',len(plan['jobs'])+len(plan['copies']))
