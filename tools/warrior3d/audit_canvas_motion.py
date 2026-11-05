"""python SCRIPT PRIVATE_WORK_ROOT [ADDITIONAL_PLAN.json ...]
Trace installed sheet hashes to authored recipes and report fitting controls.
"""
from pathlib import Path
import json,collections,sys
root=Path(sys.argv[1]).resolve()
manifest=json.loads((root/'paladin-vanilla-dimensions/install-manifest.json').read_text())
by_hash=collections.defaultdict(list)
for name,r in manifest['sheets'].items():by_hash[r['sha256'].upper()].append(name)
plans=list(root.glob('*/plan.json'))+list(root.glob('*/*/plan.json'))+list(root.glob('*/*/*/plan.json'))
plans+=list(map(Path,sys.argv[2:]))
keys=['arm_gain','motion_gain','wrist_gain','branch_gains','arm_tuck','hand_offsets','weapon_envelope','idle_weights','attachment_constraints','preserve_attack_motion']
result={};seen=set()
def chain(model,depth=0):
 if depth>6:return []
 model=Path(model);p=model.with_suffix('.motion.json')
 if not p.exists():return []
 recipe=json.loads(p.read_text())['recipe'];values={k:recipe[k] for k in keys if k in recipe};row={'model':str(model),'recipe':values,'source':recipe['source']}
 return [row]+chain(recipe['source'],depth+1)
for p in plans:
 try:plan=json.loads(p.read_text())
 except Exception:continue
 for j in plan.get('jobs',[]):
  if 'sheet' not in j or 'root' not in j or 'model' not in j:continue
  marker=Path(j['root'])/'completed.json'
  if not marker.exists():continue
  mark=json.loads(marker.read_text());names=by_hash.get(mark.get('sha256','').upper(),[])
  if not names:continue
  key=(j['model'],j.get('reference'))
  if key in seen:continue
  seen.add(key);ref=json.loads(Path(j['reference']).read_text());entry={'names':names,'plan':str(p),'model':j['model'],'reference':j['reference'],'chain':chain(j['model']),'render_constraints':{k:ref[k] for k in ['redirect_fall','shadow_distance_gain','native_root_drive','root_motion_scale','motion_root_bone'] if k in ref}}
  for n in names:result.setdefault(n,[]).append(entry)
out=root/'limit-audit.json';out.write_text(json.dumps(result,indent=2))
for n,entries in sorted(result.items()):
 e=entries[0];print(n,Path(e['plan']).parent.name,[(Path(c['model']).stem,{k:v for k,v in c['recipe'].items() if k not in ['hand_offsets','idle_weights','attachment_constraints']}) for c in e['chain']],e['render_constraints'])
print('Matched',len(result),'of',len(manifest['sheets']))
