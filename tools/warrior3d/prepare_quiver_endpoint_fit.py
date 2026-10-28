"""Blender --python SCRIPT -- PREVIOUS_PLAN NEW_WORK [BOTTOM_METRES TOP_METRES]
Rigid fit with independently requested inward endpoint movements.
"""
import bpy,json,copy,math,shutil,sys
from pathlib import Path
from mathutils import Matrix,Vector
args=sys.argv[sys.argv.index('--')+1:];old,work=map(Path,args[:2]);bottom_move,top_move=map(float,args[2:]) if len(args)>2 else (.02,.01);assert 0<=top_move<=.04 and 0<bottom_move<=.04;p=json.loads(old.read_text());previous=Path(p['work']);work=work.resolve();work.mkdir(exist_ok=False);p=copy.deepcopy(p);p['work']=str(work);p['starting_custom_manifest']=json.loads((Path(p['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text())
first=json.loads(Path(p['jobs'][0]['reference']).read_text());spec=next(e for e in first['equipment'] if e.get('town_role')=='back_quiver');bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=spec['path']);mesh=next(o.data for o in bpy.data.objects if o.type=='MESH');mesh.calc_loop_triangles();names=json.loads((previous/'triangle-parts.json').read_text());shell={'Object_2.028','Object_2.029','Object_2.088','Object_2.089','Object_2.090'};ids={k for i,t in enumerate(mesh.loop_triangles) if names[i] in shell for k in t.vertices};points=[mesh.vertices[i].co for i in ids];lo=Vector([min(v[i] for v in points) for i in range(3)]);hi=Vector([max(v[i] for v in points) for i in range(3)]);centre=(lo+hi)/2;bottom=centre.copy();bottom.z=lo.z;top=centre.copy();top.z=hi.z
M=Matrix(spec['local_transform']);base=json.loads((previous/'translation-only-references'/(p['jobs'][0]['sheet']+'.json')).read_text());Q=Matrix(next(e for e in base['equipment'] if e.get('town_role')=='back_quiver')['local_transform']);inward=-(Q.to_3x3()@Vector((0,1,0))).normalized();axis=(M.to_3x3()@Vector((1,0,0))).normalized();B=M@bottom;T=M@top;D=T-B;mid=(T+B)/2;target=inward.dot(D)+top_move-bottom_move
f=lambda a:inward.dot(Matrix.Rotation(a,3,axis)@D)-target
left,right=-math.radians(10),math.radians(10);assert f(left)*f(right)<0
for _ in range(60):
 middle=(left+right)/2
 if f(left)*f(middle)<=0:right=middle
 else:left=middle
angle=(left+right)/2;F=Matrix.Translation(mid+inward*((bottom_move+top_move)/2))@Matrix.Rotation(angle,4,axis)@Matrix.Translation(-mid)
report={'bottom_inward_metres':inward.dot(F@B-B),'top_inward_metres':inward.dot(F@T-T),'pitch_change_degrees':math.degrees(angle),'pouch_bottom_mesh_local':list(bottom),'pouch_top_mesh_local':list(top),'previous_plan':str(old.resolve()),'rigid_transform':True};assert abs(report['bottom_inward_metres']-bottom_move)<1e-6 and abs(report['top_inward_metres']-top_move)<1e-6
p['quiver_fit'].update(approved_minor_back_overlap=True,approved_minor_arrow_overlap=True,additional_inward_metres=max(bottom_move,top_move),endpoint_fit=report,selected_inward_metres=p['quiver_fit']['selected_inward_metres']+(bottom_move+top_move)/2)
for j in p['jobs']:
 root=work/'jobs'/j['sheet'];root.mkdir(parents=True);r=json.loads(Path(j['reference']).read_text());q=next(e for e in r['equipment'] if e.get('town_role')=='back_quiver');assert q['local_transform']==spec['local_transform'];q['previous_local_transform']=copy.deepcopy(q['local_transform']);q.pop('previous_asset_path',None);q['local_transform']=[list(row) for row in F@Matrix(q['local_transform'])];q['quiver_inward_revision_metres']=p['quiver_fit']['selected_inward_metres'];q['pouch_clearance_outward_metres']-=(bottom_move+top_move)/2;q['back_contour_pitch_degrees']+=math.degrees(angle);q['endpoint_fit']=report;rp=root/'reference.json';rp.write_text(json.dumps(r,indent=2));j.update(root=str(root),reference=str(rp))
for name in ['triangle-parts.json','quiver-fit-search.json','quiver-contour-search.json','translation-only-plan.json']:shutil.copy2(previous/name,work/name)
if p.get('quiver_arrow_wall_revision'):
 for name in ['arrow-fit.json','quiver-wall-clearance.json','shaft-containment.json']:shutil.copy2(previous/name,work/name)
shutil.copytree(previous/'translation-only-references',work/'translation-only-references');(work/'plan.json').write_text(json.dumps(p,indent=2));(work/'endpoint-fit.json').write_text(json.dumps(report,indent=2));print('ENDPOINT FIT',report,flush=True)
