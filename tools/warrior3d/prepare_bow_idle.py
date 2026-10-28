"""Blender --python SCRIPT -- INSTALLED_QUIVER_BOW_PLAN.json NEW_WORK
Correct only dungeon/town idle bow orientation around the unchanged grip.
"""
import bpy,sys,json,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bake_bow_equipment import bake
source,work=map(Path,sys.argv[sys.argv.index('--')+1:]);p=json.loads(source.read_text());work=work.resolve();work.mkdir(exist_ok=False);old=copy.deepcopy(p);p.update(work=str(work),equipment_family='light-bow-idle',bow_idle_revision=True,jobs=[],motions=[],copies=[],inventory={'wlb':{}},starting_custom_manifest=json.loads((Path(p['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text()))
for name in ['wlbas','wlbst']:
 j=copy.deepcopy(next(j for j in old['jobs'] if j['sheet']==name));r=json.loads(Path(j['reference']).read_text());out=work/'jobs'/name;out.mkdir(parents=True);gear=bake(Path(p['assets'])/'twoHandBow_base01.glb',out/'bow.glb',j['model'],r['rows'],mode='town',hold_tilt_degrees=10,hold_cant_degrees=20,hold_yaw_degrees=-30 if name=='wlbas' else 0);r['equipment'][0]['path']=str(gear);r.update(cell=1536,render_directions=list(range(8)),preview_caption=name.upper()+' | low idle hold, tilt 10 degrees, outward cant 20 degrees');r.pop('render_rows',None);rp=out/'reference.json';rp.write_text(json.dumps(r,indent=2));j.update(root=str(out),reference=str(rp));p['jobs'].append(j);p['motions'].append({'name':j['motion']});p['inventory']['wlb'][name]=copy.deepcopy(old['inventory']['wlb'][name])
p['bow_hold_angles']={'long_axis_tilt_degrees':10,'outward_cant_degrees':20,'dungeon_yaw_degrees':-30,'town_yaw_degrees':0,'grip_and_body_motion_unchanged':True};(work/'plan.json').write_text(json.dumps(p,indent=2))
