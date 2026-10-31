"""Blender --python SCRIPT -- CLOSED_GRIP_PLAN.json NEW_PRIVATE_WORK
Fit the closed left-hand opening to the existing staff axis. Gear and all
non-left-arm channels remain unchanged; game sheets are not installed.
"""
import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
tools=Path(__file__).resolve().parent;sys.path.insert(0,str(tools));from merge_paladin_walk import read;from author_equipped_motion import tracks,author
args=sys.argv[sys.argv.index('--')+1:];plan_file=Path(args[0]);work=Path(args[1]).resolve();assert not work.exists();work.mkdir(parents=True);plan=json.loads(plan_file.read_text());source=Path(plan['jobs'][0]['model']);g,b=read(source);tr=tracks(g,b);names={n.get('name'):i for i,n in enumerate(g['nodes'])};parents={c:i for i,n in enumerate(g['nodes']) for c in n.get('children',[])};B=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)));bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(source));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');targets=[];corrections=[]
def worlds(row):
 cache={}
 def get(i):
  if i not in cache:
   node=g['nodes'][i]
   def value(path,default):return tr[i,path][1][row] if (i,path) in tr else node.get(path,default)
   if 'matrix' in node:m=Matrix([node['matrix'][j:j+4] for j in range(0,16,4)]).transposed()
   else:
    q=value('rotation',[0,0,0,1]);m=Matrix.LocRotScale(Vector(value('translation',[0,0,0])),Quaternion((float(q[3]),*map(float,q[:3]))),Vector(value('scale',[1,1,1])))
   cache[i]=(get(parents[i]) if i in parents else Matrix.Identity(4))@m
  return cache[i]
 return get
for row in range(16):
 bpy.context.scene.frame_set(row);bpy.context.view_layer.update();h=rig.matrix_world@rig.pose.bones['hand.L'].matrix;r=rig.matrix_world@rig.pose.bones['hand.R'].matrix@Vector((.0425,.0825,-.002));p=h@Vector((0,.05,0));axis=(p-r).normalized();up=h.to_3x3()@Vector((0,0,1));axis=axis if up.dot(axis)>=0 else -axis;rotation=up.rotation_difference(axis)@h.to_quaternion();desired=Matrix.LocRotScale(Vector((0,0,0)),rotation,h.to_scale());desired.translation=p-desired.to_3x3()@Vector((-.04,.065,0));gw=worlds(row)(names['hand.L']);C=(B@gw).inverted()@h;corrections.append(C);target=B.inverted()@desired@C.inverted();q=target.to_quaternion();targets.append({'position':list(target.translation),'rotation_wxyz':[q.w,q.x,q.y,q.z]})
error=max(abs(C[i][j]-corrections[0][i][j]) for C in corrections for i in range(4) for j in range(4));print('Bone basis correction consistency',error,flush=True);assert error<1e-4
recipe={'name':'Selected Sorcerer, staff through left closed-hand centre','source':str(source),'frames':list(range(16)),'arms':[],'preserve_attack_motion':True,'hand_grip_poses':{'L':targets}};rp=work/'recipe.json';rp.write_text(json.dumps(recipe,indent=2));model=work/'sorcerer.glb';author(rp,model);plan['work']=str(work);j=plan['jobs'][0];out=work/'preview';out.mkdir(exist_ok=True);ref=json.loads(Path(j['reference']).read_text());ref['preview_caption']='Original Sorcerer | 30cm slide / centred left grip';reference=out/'reference.json';reference.write_text(json.dumps(ref,indent=2));j.update(model=str(model),root=str(out),reference=str(reference));(work/'plan.json').write_text(json.dumps(plan,indent=2))


