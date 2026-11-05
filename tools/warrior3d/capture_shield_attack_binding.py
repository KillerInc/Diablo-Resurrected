"""Capture an attack-only shield attachment using the existing weapon.L socket.

Blender --python SCRIPT -- APPROVED.blend BODY.glb REFERENCE.json OUTPUT.json
The source scene must show the approved frame-zero forearm mount. The output is
an authored attachment profile; neither meshes nor textures are embedded.
"""
import bpy,json,sys
import numpy as np
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
scene,body,reference,output=map(Path,sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,str(Path(__file__).resolve().parent));from merge_paladin_walk import read;from author_equipped_motion import tracks
bpy.ops.wm.open_mainfile(filepath=str(scene.resolve()));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(0);bpy.context.view_layer.update();shield=next(o for o in bpy.data.objects if o.get('d1r_asset')=='Shield_S15_Warrior_Red.glb');g,b=read(body);tr=tracks(g,b);names={n.get('name'):i for i,n in enumerate(g['nodes'])};parents={c:i for i,n in enumerate(g['nodes']) for c in n.get('children',[])};cache={}
def world(i):
 if i not in cache:
  n=g['nodes'][i]
  if 'matrix' in n:m=Matrix([n['matrix'][j:j+4] for j in range(0,16,4)]).transposed()
  else:
   v={p:tr[i,p][1][0] if (i,p) in tr else n.get(p,d) for p,d in [('translation',[0,0,0]),('rotation',[0,0,0,1]),('scale',[1,1,1])]};q=v['rotation'];m=Matrix.LocRotScale(Vector(v['translation']),Quaternion((q[3],*q[:3])),Vector(v['scale']))
  cache[i]=world(parents[i])@m if i in parents else m
 return cache[i]
def b2g(v):return Vector((v.x,v.z,-v.y))
def g2b(v):return Vector((v.x,-v.z,v.y))
weapon='weapon.L';hand='hand.L';desc=[rig.data.bones[weapon]]+list(rig.data.bones[weapon].children_recursive);weighted=0
for obj in bpy.data.objects:
 if obj.type!='MESH' or obj.get('d1r_equipment'):continue
 groups={obj.vertex_groups[n.name].index for n in desc if obj.vertex_groups.get(n.name)}
 weighted+=sum(1 for v in obj.data.vertices for item in v.groups if item.group in groups and item.weight>1e-6)
assert weighted==0,('Attachment bone deforms body vertices',weighted)
item=json.loads(reference.read_text())['equipment'][0];gw=world(names[weapon]);gh=world(names[hand]);delta=rig.matrix_world@rig.pose.bones[hand].head-g2b(gh.translation)
for n in [weapon,'forearm.L']:assert ((rig.matrix_world@rig.pose.bones[n].head-g2b(world(names[n]).translation))-delta).length<1e-4
grip=b2g(shield.matrix_world@Vector(item['grip'])-delta);points=np.array([list(shield.matrix_world@v.co) for v in shield.data.vertices]);vals,vec=np.linalg.eigh(np.cov(points.T));normal=Vector(vec[:,0]);normal.negate() if normal.dot(Vector((0,-1,0)))<0 else None;local=(rig.matrix_world@rig.pose.bones[weapon].matrix).inverted()@shield.matrix_world
normal_g=b2g(normal);up_g=Vector((0,1,0))-normal_g*normal_g.y;up_g.normalize()
profile={'grip':item['grip'],'shield_grip_revision':item.get('shield_grip_revision','uncorrected'),'up_local':list(gw.to_3x3().inverted()@up_g),'filename':'Shield_S15_Warrior_Red.glb','bone':weapon,'local_transform':[list(row) for row in local],'hand':hand,'normal_local':list(gw.to_3x3().transposed()@b2g(normal)),'grip_local':list(gw.inverted()@grip),'hand_grip_local':list(gh.inverted()@grip),'scale':list(gw.to_scale()),'weighted_body_vertices':weighted,'source_body':'shield-idle.glb'};output.write_text(json.dumps(profile,indent=2));print(profile,flush=True)
