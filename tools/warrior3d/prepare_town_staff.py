"""Blender --python SCRIPT -- INSTALLED_STAFF_PLAN NEW_WORK
Prepare left-hand town staff carry matching vanilla, retaining approved gait.
"""
import bpy,json,math,sys,copy
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
tools=Path(__file__).resolve().parent;sys.path.insert(0,str(tools));from author_equipped_motion import author,tracks;from merge_paladin_walk import read;from bake_bow_equipment import keys
args=sys.argv[sys.argv.index('--')+1:];old=json.loads(Path(args[0]).read_text());work=Path(args[1]).resolve();assert not work.exists();work.mkdir(parents=True);plan=copy.deepcopy(old);plan.update(work=str(work),equipment_family='light-town-staff',starting_custom_manifest=json.loads((Path(old['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text()),jobs=[],motions=[],copies=[],inventory={'wlt':{}},town_staff_revision=True,staff_town_carry='upright left hand, vanilla style; short stride preserved');B=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)));calibration=[]
for action in ['st','wl']:
 name='wlt'+action;donor=next(j for j in old['jobs'] if j['sheet']==name);ref=json.loads(Path(donor['reference']).read_text());rows=ref['rows'];base=work/(name+'-closed.glb');recipe=work/(name+'-closed-recipe.json');recipe.write_text(json.dumps({'name':name+' left fingers closed','source':donor['model'],'frames':list(range(rows)),'arms':[],'idle':str(Path(old['previous'])/'axe-options/sources/idle.glb'),'finger_grip':['L'],'preserve_grip_wrist_motion':True},indent=2));author(recipe,base)
 g,blob=read(base);tr=tracks(g,blob);names={n.get('name'):i for i,n in enumerate(g['nodes'])};parents={c:i for i,n in enumerate(g['nodes']) for c in n.get('children',[])}
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
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(base));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rest=(rig.data.bones['forearm.L'].matrix_local.inverted()@rig.data.bones['hand.L'].matrix_local).to_quaternion();grip=Vector((-.04,.065,0));targets=[];poses=[];reviews=[];previous=None
 for row in range(rows):
  bpy.context.scene.frame_set(row);bpy.context.view_layer.update();h=rig.matrix_world@rig.pose.bones['hand.L'].matrix;fq=(rig.matrix_world@rig.pose.bones['forearm.L'].matrix).to_quaternion();A=rig.matrix_world@rig.pose.bones['upperArm.L'].head;E0=rig.matrix_world@rig.pose.bones['forearm.L'].head;H0=h.translation;pelvis=rig.matrix_world@rig.pose.bones['pelvis'].head;phase=2*math.pi*row/rows;lean=math.radians(8)*math.sin(phase) if action=='wl' else 0;z=Vector((0,math.sin(lean),-math.cos(lean)));P=pelvis+Vector((.36,-.26,.14));upper=(E0-A).length;lower=(H0-E0).length;best=None
  for slide in [-.05,-.025,0,.025,.05]:
   centre=P+z*slide
   for pole_degrees in range(-100,101,20):
    q=h.to_quaternion();valid=True
    for iteration in range(20):
     H=centre-q@grip;D=H-A;distance=D.length
     if distance>upper+lower-.003 or distance<abs(upper-lower)+.003:valid=False;break
     D.normalize();pole=E0-A;pole-=D*pole.dot(D)
     if pole.length<1e-5:valid=False;break
     pole=Quaternion(D,math.radians(pole_degrees))@pole.normalized();along=(upper*upper-lower*lower+distance*distance)/(2*distance);E=A+D*along+pole*max(0,upper*upper-along*along)**.5;F=(H-E).normalized();uq=(E0-A).rotation_difference(E-A);eq=(uq@(H0-E0)).rotation_difference(H-E);baseq=eq@uq@fq;neutral=baseq@rest;v=neutral@Vector((0,0,1));a=v-F*v.dot(F);b=z-F*z.dot(F)
     if min(a.length,b.length)<1e-5:valid=False;break
     a.normalize();b.normalize();twist=math.atan2(F.dot(a.cross(b)),a.dot(b));twist=max(-math.radians(80),min(math.radians(80),twist));forearm=Quaternion(F,twist)@baseq;neutral=forearm@rest;delta=(neutral@Vector((0,0,1))).rotation_difference(z);nextq=delta@neutral
     if nextq.rotation_difference(q).angle<1e-5:q=nextq;break
     q=q.slerp(nextq,.7)
    if not valid:continue
    desired_H=centre-q@grip;bend=math.degrees(delta.angle)
    if (desired_H-H).length>.001 or bend>25:continue
    jump=math.degrees(q.rotation_difference(previous).angle) if previous is not None else 0;cost=.2*bend*bend+.025*math.degrees(twist)**2+slide*slide*3000+(E-E0).length_squared*400+.02*jump*jump
    if best is None or cost<best[0]:best=(cost,desired_H.copy(),q.copy(),E.copy(),math.degrees(twist),centre.copy(),bend)
  assert best is not None,(name,row,'no town grip fit',list(A),list(E0),list(H0),list(P),upper,lower)
  _,H,q,E,twist,centre,bend=best;previous=q.copy();desired=Matrix.LocRotScale(H,q,h.to_scale());gw=worlds(row)(names['hand.L']);C=(B@gw).inverted()@h;target=B.inverted()@desired@C.inverted();qt=target.to_quaternion();targets.append({'position':list(target.translation),'rotation_wxyz':[qt.w,qt.x,qt.y,qt.z],'elbow':list(B.inverted()@E),'forearm_twist_degrees':twist});poses.append((centre,z));reviews.append({'row':row,'wrist_delta_degrees':bend,'forearm_twist_degrees':twist});print('TOWN GRIP',name,row,bend,flush=True)
 rp=work/(name+'-recipe.json');rp.write_text(json.dumps({'name':name+' upright left-hand staff town carry','source':str(base),'frames':list(range(rows)),'arms':[],'hand_grip_poses':{'L':targets}},indent=2));model=work/(name+'-body.glb');author(rp,model)
 bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(model));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(Path(old['assets'])/'twoHandStaff_base01.glb'));o=next(o for o in set(bpy.data.objects)-before if o.type=='MESH');raw=[o.matrix_world@v.co for v in o.data.vertices];positions=[];mounts=[]
 for row,(centre,z) in enumerate(poses):
  scene.frame_set(row);bpy.context.view_layer.update();hand=rig.matrix_world@rig.pose.bones['hand.L'].matrix;centre=hand@grip;x=Vector((1,0,0));basis=Matrix((x,z,x.cross(z))).transposed().to_4x4()@Matrix.Scale(.8,4);minimum=min((basis.to_3x3()@v).z for v in raw);grip_y=(centre.z+minimum-.05)/basis[2][1];basis.translation=centre-basis.to_3x3()@Vector((0,grip_y,0));local=hand.inverted()@basis;positions.append([local@v for v in raw]);mounts.append({'row':row,'grip_local_y':grip_y,'grip_world':list(centre),'shaft_axis':list(z)})
 keys(o,positions);o.parent=None;o.matrix_world=Matrix.Identity(4);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);scene.frame_start=0;scene.frame_end=rows-1;scene.frame_set(0);staff=work/(name+'-staff.glb');bpy.ops.export_scene.gltf(filepath=str(staff),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='SCENE',export_anim_scene_split_object=False,export_frame_range=True,export_force_sampling=True)
 ref.update(equipment=[{'path':str(staff),'bone':'hand.L','local_transform':[list(r) for r in Matrix.Identity(4)],'town_role':'held_staff','allow_hand_grip_contact':True}],preview_caption=name.upper()+' | vanilla-style left-hand staff town carry',preview_prefix=name,render_directions=list(range(8)),root_anchor_frame=0)
 for key in ['pose_offsets','direction_pose_offsets']:ref.pop(key,None)
 out=work/'jobs'/name;out.mkdir(parents=True,exist_ok=True);reference=out/'reference.json';reference.write_text(json.dumps(ref,indent=2));job=copy.deepcopy(donor);job.update(model=str(model),root=str(out),reference=str(reference));plan['jobs'].append(job);plan['motions'].append({'name':job['motion']});plan['inventory']['wlt'][name]=copy.deepcopy(old['inventory']['wlt'][name]);(work/(name+'-fit.json')).write_text(json.dumps({'poses':reviews,'mounts':mounts,'original_town_model':donor['model'],'approved_short_stride_preserved':True},indent=2))
(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared held-left town staff idle and short walk',flush=True)


