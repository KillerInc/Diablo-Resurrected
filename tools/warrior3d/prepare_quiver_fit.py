"""python SCRIPT FULL_BOW_PLAN LATEST_IDLE_PLAN NEW_WORK
Rebase a quiver-only revision onto all nine currently approved bow actions.
"""
import json,copy,sys,shutil
from pathlib import Path
full,idles,work=map(Path,sys.argv[1:]);old=json.loads(full.read_text());idle=json.loads(idles.read_text());work=work.resolve();work.mkdir(exist_ok=False);p=copy.deepcopy(old);manifest=json.loads((Path(old['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text());p.update(work=str(work),jobs=[],motions=[],copies=[],inventory={'wlb':{}},starting_custom_manifest=manifest,equipment_family='light-bow',quiver_fit_revision=True)
overrides={j['sheet']:j for j in idle['jobs']};mounts=[]
for original in old['jobs']:
 j=copy.deepcopy(overrides.get(original['sheet'],original));r=json.loads(Path(j['reference']).read_text());name=j['sheet'];inv=copy.deepcopy((idle if name in overrides else old)['inventory']['wlb'][name]);old_root=Path(j['root']);root=work/'jobs'/name;root.mkdir(parents=True)
 meta=old_root/'frames/render.json'
 if meta.exists():
  m=json.loads(meta.read_text())
  if m.get('direction_image_offsets'):r['direction_image_offsets']=m['direction_image_offsets']
 q=next(e for e in r['equipment'] if e.get('town_role')=='back_quiver');mounts.append(q['local_transform']);r.pop('render_rows',None);r['render_directions']=list(range(8));rp=root/'reference.json';rp.write_text(json.dumps(r,indent=2));j.update(root=str(root),reference=str(rp));p['jobs'].append(j);p['motions'].append({'name':j['motion']});p['inventory']['wlb'][name]=inv
assert len(p['jobs'])==9 and all(m==mounts[0] for m in mounts)
shutil.copy2(Path(old['work'])/'triangle-parts.json',work/'triangle-parts.json');(work/'plan.json').write_text(json.dumps(p,indent=2))
