"""python SCRIPT PRIVATE_WORKSPACE
Prepare nine bow revisions from existing approved bow/town/cast models.
Input art and source poses stay intact; run mount_bow_quiver.py next.
"""
from pathlib import Path
import json,copy,shutil,sys
root=Path(sys.argv[1]).resolve();w=root/'warrior-3d/quiver-bow-final';w.mkdir(exist_ok=True);old=r'C:\Users\kille\.codex\.chatgpt-projects\g-p-6ad48fbb0ae08191a500e55129b616e6'
def fix(v):
 if isinstance(v,str):return v.replace(old,str(root))
 if isinstance(v,list):return [fix(x) for x in v]
 if isinstance(v,dict):return {k:fix(x) for k,x in v.items()}
 return v
p=fix(json.loads((root/'warrior-3d/bow-set-final/plan.json').read_text()));town=fix(json.loads((root/'warrior-3d/town-bow-hand/plan.json').read_text()));p['jobs']=[j for j in p['jobs'] if j['action'] not in ['st','wl']]+town['jobs'];p['copies']=[];p['work']=str(w);p['motions']=[];p['starting_custom_manifest']=json.loads((root/'warrior-3d/paladin-vanilla-dimensions/install-manifest.json').read_text());p['quiver_revision']=True
cast=root/'warrior-3d/paladin-fire-bubble/gizmo-final/Paladin-fire-cast.glb'
for a,rp in [('fm',root/'warrior-3d/paladin-fire-bubble/gizmo-final/reference.json'),('lm',root/'warrior-3d/paladin-lightning/reference.json'),('qm',root/'warrior-3d/paladin-magic/option2-ground-radius/reference.json')]:p['jobs'].append(dict(sheet='wlb'+a,code='wlb',action=a,model=str(cast),motion='wlb'+a,reference=str(rp)))
for j in p['jobs']:
 dest=w/'jobs'/j['sheet'];dest.mkdir(parents=True,exist_ok=True);ref=fix(json.loads(Path(j['reference']).read_text()));ref.update(sheet=j['sheet']+'.png',preview_prefix=j['sheet'],root_anchor_frame=ref.get('root_anchor_frame',1));ref.pop('render_rows',None);ref['render_directions']=list(range(8));ref['cell']=1536
 j['model']=str(Path(j['model']).resolve());ref['equipment']=ref.get('equipment',[]);j['reference']=str(dest/'reference.json');j['root']=str(dest);Path(j['reference']).write_text(json.dumps(ref,indent=2));p['motions'].append({'name':j['motion']})
 if j['sheet'] not in p['inventory']['wlb']:raise RuntimeError(j['sheet'])
 if ref['rows']>p['inventory']['wlb'][j['sheet']]['rows']:j['output_rows']=p['inventory']['wlb'][j['sheet']]['rows']
(w/'plan.json').write_text(json.dumps(p,indent=2));print(w)
