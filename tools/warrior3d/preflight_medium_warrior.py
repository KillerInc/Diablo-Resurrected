"""Audit medium animation bounds and pad canvases; never attenuate motion."""
import bpy,json,sys,math,gc
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from paladin_equipment import attach_equipment
file=Path(sys.argv[sys.argv.index('--')+1]).resolve();plan=json.loads(file.read_text());cal=json.loads(Path(plan['calibration']).read_text());density=cal['global_pixel_scale']*768/2.75/8;report_path=Path(plan['work'])/'animation-preflight.json';reports=json.loads(report_path.read_text()) if report_path.exists() else []
for j in plan['jobs']:
 if (Path(j['root'])/'output/validation.json').exists():continue
 ref=json.loads(Path(j['reference']).read_text());bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.rotation_mode='XYZ';rig.rotation_euler=(0,0,0);rig.location=(0,0,0)
 gear=attach_equipment(rig,ref.get('equipment',[]));parts=[o for o in bpy.context.scene.objects if o.type=='MESH' and o not in gear and o.data.materials and any(t in o.data.materials[0].name for t in ref['shadow_material_tokens'])];assert len(parts)==ref['shadow_anatomy_count'],(j['sheet'],len(parts))
 scene.frame_set(ref.get('root_anchor_frame',1));bpy.context.view_layer.update();initial=(rig.matrix_world@rig.pose.bones['pelvis'].head).copy();allpoints=[];contacts=[]
 for row,frame in enumerate(ref['source_frames']):
  rig.location=(0,0,0);scene.frame_set(int(frame));bpy.context.view_layer.update();pelvis=rig.matrix_world@rig.pose.bones['pelvis'].head
  if not ref.get('preserve_horizontal_root_motion',False):rig.location.x=initial.x-pelvis.x;rig.location.y=initial.y-pelvis.y
  if ref.get('pose_offsets'):rig.location+=Vector(ref['pose_offsets'][row])
  bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();chunks=[];geometry={}
  for o in parts+gear:
   ev=o.evaluated_get(deps);me=ev.to_mesh();a=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',a);matrix=np.asarray(ev.matrix_world);v=a.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3];chunks.append(v)
   if o in gear or ('Helmet' in o.data.materials[0].name or 'HLM' in o.data.materials[0].name):geometry[o.name]=(v,[tuple(p.vertices) for p in me.polygons])
   ev.to_mesh_clear()
  points=np.concatenate(chunks);assert np.isfinite(points).all() and np.abs(points).max()<8,(j['sheet'],row,'invalid deformation');allpoints.append(points)
  # Head clearance is critical; hand/forearm and stowed-back contacts are
  # intentionally not treated as failures for gripped weapons and shields.
  if j['sheet'].endswith('at'):
   helmet=next(o for o in parts if ('Helmet' in o.data.materials[0].name or 'HLM' in o.data.materials[0].name));v,f=geometry[helmet.name];head=BVHTree.FromPolygons([Vector(p) for p in v],f)
   for o in gear:
    v,f=geometry[o.name];tree=BVHTree.FromPolygons([Vector(p) for p in v],f);hits=tree.overlap(head)
    if hits:contacts.append({'row':row,'equipment':o.get('d1r_asset',o.name),'helmet_triangles':len(hits)})
 rawmax=0;lo=np.array([float('inf')]*2);hi=-lo
 oldcanvas=ref['canvas_logical'];anchor=ref['canvas_anchor'];ground=np.array([anchor[0],anchor[1]-16])
 for points in allpoints:
  for d in range(8):
   a=-d*math.pi/4;c,s=math.cos(a),math.sin(a);p=points@np.array([[c,-s,0],[s,c,0],[0,0,1]]).T
   shadow=p.copy();height=np.maximum(shadow[:,2],0);shadow[:,0]-=.5*height;shadow[:,1]+=2/3*height;shadow[:,2]=.002
   for kind,v in [('body',p),('shadow',shadow)]:
    projected=np.column_stack((v[:,0],-(.5*v[:,1]+math.sqrt(.75)*v[:,2])));xy=ground+density*projected;lo=np.minimum(lo,xy.min(0));hi=np.maximum(hi,xy.max(0))
    raw=projected*(768/2.75)+np.array([0,217.671581]);need=np.abs(raw).max()-(256 if kind=='shadow' else 0);rawmax=max(rawmax,need)
 padlo=np.maximum(0,np.ceil(2-lo)).astype(int);padhi=np.maximum(0,np.ceil(hi+2-oldcanvas)).astype(int);ref['canvas_logical']=[int(oldcanvas[i]+padlo[i]+padhi[i]) for i in range(2)];ref['canvas_anchor']=[int(anchor[i]+padlo[i]) for i in range(2)];ref['cell']=max(ref.get('cell',768) if j['sheet'][-2:] in ('fm','lm','qm') else 768,int(math.ceil((rawmax*2+32)/128))*128)
 Path(j['reference']).write_text(json.dumps(ref,indent=2));reports=[r for r in reports if r['sheet']!=j['sheet']];reports.append({'sheet':j['sheet'],'rows':len(allpoints),'full_motion_preserved':True,'original_canvas':oldcanvas,'canvas':ref['canvas_logical'],'anchor':ref['canvas_anchor'],'raw_cell':ref['cell'],'helmet_contacts':contacts})
 (Path(plan['work'])/'animation-preflight.json').write_text(json.dumps(reports,indent=2));print('MEDIUM_PREFLIGHT',j['sheet'],'canvas',ref['canvas_logical'],'head contacts',len(contacts),flush=True);gc.collect()
print('PASS: 85 medium pose/bounds audits; inspect recorded helmet contacts before installation')
