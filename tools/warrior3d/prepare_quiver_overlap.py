"""python SCRIPT PREVIOUS_QUIVER_PLAN NEW_WORK [INWARD_METRES]
Apply a small, explicitly approved back overlap without changing any pose.
"""
import copy,json,math,shutil,sys
from pathlib import Path
old=Path(sys.argv[1]);work=Path(sys.argv[2]).resolve();distance=float(sys.argv[3]) if len(sys.argv)>3 else .02
assert 0<distance<=.02
p=json.loads(old.read_text());previous=Path(p['work']);work.mkdir(exist_ok=False);p=copy.deepcopy(p);p['work']=str(work);p['starting_custom_manifest']=json.loads((Path(p['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text())
p['quiver_fit']['approved_minor_back_overlap']=True;p['quiver_fit']['additional_inward_metres']=distance;p['quiver_fit']['selected_inward_metres']+=distance
for j in p['jobs']:
 root=work/'jobs'/j['sheet'];root.mkdir(parents=True);r=json.loads(Path(j['reference']).read_text());q=next(e for e in r['equipment'] if e.get('town_role')=='back_quiver');q['previous_local_transform']=copy.deepcopy(q['local_transform'])
 base=json.loads((previous/'translation-only-references'/(j['sheet']+'.json')).read_text());M=next(e for e in base['equipment'] if e.get('town_role')=='back_quiver')['local_transform'];axis=[M[i][1] for i in range(3)];length=math.sqrt(sum(v*v for v in axis))
 for i in range(3):q['local_transform'][i][3]-=distance*axis[i]/length
 q['quiver_inward_revision_metres']=p['quiver_fit']['selected_inward_metres'];q['pouch_clearance_outward_metres']-=distance;rp=root/'reference.json';rp.write_text(json.dumps(r,indent=2));j.update(root=str(root),reference=str(rp))
for name in ['triangle-parts.json','quiver-fit-search.json','quiver-contour-search.json','translation-only-plan.json']:shutil.copy2(previous/name,work/name)
shutil.copytree(previous/'translation-only-references',work/'translation-only-references');(work/'plan.json').write_text(json.dumps(p,indent=2))
