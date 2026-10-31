"""Author a grounded punch or six-pose hit draft from the current idle skeleton.

Blender --python SCRIPT -- IDLE.glb OUTPUT.glb [punch|hit]
Arm and planted-leg IK are solved in glTF world coordinates. Rotations and a
small root weight shift change; geometry, skin bindings and nodes are preserved. No glTF
scene re-export is used. This is a preview candidate, not an installed action.
"""
import copy,json,math,struct,sys
from pathlib import Path
import numpy as np
from mathutils import Matrix,Quaternion,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from merge_paladin_walk import read

arguments=sys.argv[sys.argv.index('--')+1:]
source,destination=map(Path,arguments[:2]);action=arguments[2] if len(arguments)>2 else 'punch'
assert action in ['punch','hit']
g,original_blob=read(source);original=copy.deepcopy(g);blob=bytearray(original_blob)
names={n.get('name'):i for i,n in enumerate(g['nodes'])}
parents={ch:i for i,n in enumerate(g['nodes']) for ch in n.get('children',[])}
tracks={}
for ch in g['animations'][0]['channels']:
    path=ch['target']['path'];sm=g['animations'][0]['samplers'][ch['sampler']]
    ac=g['accessors'][sm['output']];v=g['bufferViews'][ac['bufferView']]
    assert ac['componentType']==5126 and 'byteStride' not in v
    width=4 if path=='rotation' else 3
    tracks[(ch['target']['node'],path)]=np.frombuffer(original_blob,dtype='<f4',count=ac['count']*width,offset=v.get('byteOffset',0)+ac.get('byteOffset',0)).reshape(-1,width)[0].copy()

def quaternion(xyzw):return Quaternion((xyzw[3],xyzw[0],xyzw[1],xyzw[2]))
def components(q):return [q.x,q.y,q.z,q.w]
base=[]
for i,node in enumerate(g['nodes']):
    base.append({p:tracks.get((i,p),np.array(node.get(p,default))).copy()
                 for p,default in [('translation',[0,0,0]),('rotation',[0,0,0,1]),('scale',[1,1,1])]})

def world_matrices(pose):
    cache={}
    def world(i):
        if i not in cache:
            node=g['nodes'][i]
            local=Matrix([node['matrix'][j:j+4] for j in range(0,16,4)]).transposed() if 'matrix' in node else Matrix.LocRotScale(Vector(pose[i]['translation']),quaternion(pose[i]['rotation']),Vector(pose[i]['scale']))
            cache[i]=(world(parents[i])@local) if i in parents else local
        return cache[i]
    for i in range(len(pose)):world(i)
    return cache

initial=world_matrices(base)
def position(world,name):return world[names[name]].translation.copy()
def set_world_rotation(pose,name,rotation):
    i=names[name];world=world_matrices(pose)
    parent=world[parents[i]].to_quaternion() if i in parents else Quaternion()
    pose[i]['rotation']=np.array(components((parent.inverted()@rotation).normalized()))

def arm(pose,side,target,guard):
    u,e,h=[n+'.'+side for n in ['upperArm','forearm','hand']]
    world=world_matrices(pose);shoulder=position(world,u);elbow=position(world,e);wrist=position(world,h)
    l1=(elbow-shoulder).length;l2=(wrist-elbow).length;direction=target-shoulder
    distance=max(abs(l1-l2)+.005,min(direction.length,(l1+l2)*.97));direction.normalize();target=shoulder+direction*distance
    sign=-1 if side=='R' else 1
    hint=shoulder+Vector((sign*.30,-.28,.08))
    hint=elbow.lerp(hint,guard)
    perpendicular=hint-shoulder;perpendicular-=direction*perpendicular.dot(direction)
    if perpendicular.length<1e-5:perpendicular=Vector((sign,0,0)).cross(direction)
    perpendicular.normalize()
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    desired_elbow=shoulder+direction*along+perpendicular*math.sqrt(max(0,l1*l1-along*along))
    rotation=(elbow-shoulder).rotation_difference(desired_elbow-shoulder)@world[names[u]].to_quaternion()
    set_world_rotation(pose,u,rotation)
    world=world_matrices(pose);elbow=position(world,e);wrist=position(world,h)
    rotation=(wrist-elbow).rotation_difference(target-elbow)@world[names[e]].to_quaternion()
    set_world_rotation(pose,e,rotation)
    return list(position(world_matrices(pose),h))

def planted_leg(pose,side,amount):
    u,e,h=[n+'.'+side for n in ['thigh','shin','ankle']]
    world=world_matrices(pose);hip=position(world,u);knee=position(world,e);ankle=position(world,h)
    target=position(initial,h);l1=(knee-hip).length;l2=(ankle-knee).length
    direction=target-hip;distance=direction.length
    assert abs(l1-l2)<distance<l1+l2,('leg reach',side,distance,l1+l2)
    direction.normalize();hint=position(initial,e)+Vector((0,-.02,.14*amount))
    perpendicular=hint-hip;perpendicular-=direction*perpendicular.dot(direction);perpendicular.normalize()
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    desired=hip+direction*along+perpendicular*math.sqrt(max(0,l1*l1-along*along))
    set_world_rotation(pose,u,(knee-hip).rotation_difference(desired-hip)@world[names[u]].to_quaternion())
    world=world_matrices(pose);knee=position(world,e);ankle=position(world,h)
    set_world_rotation(pose,e,(ankle-knee).rotation_difference(target-knee)@world[names[e]].to_quaternion())
    set_world_rotation(pose,h,initial[names[h]].to_quaternion())

guard=[0,.12,.38,.72,.96,1,1,1,1,1,1,.97,.86,.65,.32,0]
strike=[0,0,0,0,0,.04,.22,.72,1,.80,.38,.09,0,0,0,0]
yaw=[0,0,-.025,-.07,-.12,-.15,-.12,.015,.20,.17,.09,.025,-.015,-.01,0,0]
hip_yaw=[0,0,-.02,-.055,-.10,-.12,-.085,.02,.20,.23,.16,.10,.045,.01,-.008,0]
weight_x=[0,-.005,-.012,-.025,-.03,-.02,0,.03,.055,.045,.03,.015,0,-.005,-.003,0]
weight_y=[0,-.003,-.01,-.02,-.025,-.025,-.018,-.005,0,-.003,-.01,-.015,-.012,-.007,-.002,0]
weight_z=[0,0,-.01,-.025,-.035,-.02,.01,.04,.07,.06,.04,.025,.01,0,0,0]
if action=='hit':
    guard=[0,.8,1,.65,.25,0];strike=[0]*6
    yaw=[0,.05,.10,.06,.02,0];hip_yaw=[0,-.02,-.045,-.03,-.01,0]
    weight_x=[0,-.008,-.016,-.01,-.003,0]
    weight_y=[0,-.015,-.025,-.015,-.005,0]
    weight_z=[0,-.03,-.055,-.035,-.012,0]
rows=len(guard)
poses=[];measure=[];modified={'root','chest','upperArm.R','forearm.R','upperArm.L','forearm.L','hand.R','hand.L','head'}
modified|={n+'.'+s for n in ['thigh','shin','ankle'] for s in ['L','R']}
modified|={f'm{number:03d}.{side}' for number in range(14,26) for side in ['R','L'] if f'm{number:03d}.{side}' in names}
for row in range(rows):
    pose=copy.deepcopy(base)
    if guard[row]:
        shift=Vector((weight_x[row],weight_y[row],weight_z[row]));turn=Quaternion((0,1,0),hip_yaw[row])
        pose[names['root']]['translation']=base[names['root']]['translation']+np.array(shift)
        set_world_rotation(pose,'root',turn@initial[names['root']].to_quaternion())
        # Lower the hips just enough to keep both planted legs within reach.
        world=world_matrices(pose);lower=0
        for side in ['R','L']:
            hip=position(world,'thigh.'+side);knee=position(world,'shin.'+side);ankle=position(world,'ankle.'+side);target=position(initial,'ankle.'+side)
            reach=((knee-hip).length+(ankle-knee).length)*.995
            horizontal=(hip.x-target.x)**2+(hip.z-target.z)**2
            assert horizontal<reach*reach
            lower=max(lower,hip.y-target.y-math.sqrt(reach*reach-horizontal))
        pose[names['root']]['translation'][1]-=max(0,lower)
        for side in ['R','L']:planted_leg(pose,side,guard[row])
        lean=-.14*guard[row] if action=='hit' else .085*strike[row]
        head_lean=-.18*guard[row] if action=='hit' else .025*strike[row]
        chest=Quaternion((0,1,0),hip_yaw[row]+yaw[row])@Quaternion((1,0,0),lean)@initial[names['chest']].to_quaternion()
        set_world_rotation(pose,'chest',chest)
        set_world_rotation(pose,'head',Quaternion((0,1,0),.25*hip_yaw[row])@Quaternion((1,0,0),head_lean)@initial[names['head']].to_quaternion())
        world=world_matrices(pose)
        for side in ['R','L']:
            shoulder=position(world,'upperArm.'+side);sign=-1 if side=='R' else 1
            ready=turn@Vector((sign*.25,1.22,.17) if action=='hit' else (sign*.23,1.30,.24))+shift
            target=ready
            if side=='R':
                target=ready.lerp(shoulder+Vector((.06,-.035,.52)),strike[row])
                target.y+=.045*math.sin(math.pi*strike[row])
            else:target+=Vector((.025*strike[row],.045*strike[row],-.045*strike[row]))
            target=position(initial,'hand.'+side).lerp(target,guard[row])
            arm(pose,side,target,guard[row])
            world=world_matrices(pose)
            wrist=position(world,'hand.'+side);knuckles=position(world,'handEnd.'+side)
            forearm=wrist-position(world,'forearm.'+side)
            original_hand=world[names['hand.'+side]].to_quaternion()
            straight=(knuckles-wrist).rotation_difference(forearm)@original_hand
            if side=='R':straight=Quaternion(forearm.normalized(),-.5*strike[row])@straight
            set_world_rotation(pose,'hand.'+side,original_hand.slerp(straight,guard[row]))
            world=world_matrices(pose)
            lateral=world[names['handEnd.'+side]].to_3x3().col[2].normalized()
            # Four finger chains fold into a fist; preserve the source thumb.
            for first in [14,17,20,23]:
                for joint,degrees in enumerate([50,70,40]):
                    finger=f'm{first+joint:03d}.{side}'
                    if finger not in names:continue
                    world=world_matrices(pose)
                    bend=Quaternion(lateral,math.radians(degrees)*guard[row]*(.35 if action=='hit' else 1)*(-1 if side=='R' else 1))
                    set_world_rotation(pose,finger,bend@world[names[finger]].to_quaternion())
    world=world_matrices(pose)
    measure.append({'row':row,'root_translation':pose[names['root']]['translation'].tolist(),'right_wrist':list(position(world,'hand.R')),'left_wrist':list(position(world,'hand.L')),'right_elbow':list(position(world,'forearm.R')),'right_shoulder':list(position(world,'upperArm.R'))})
    poses.append(pose)

def add(data,kind):
    data=np.asarray(data,dtype='<f4');blob.extend(b'\0'*((-len(blob))%4));offset=len(blob);raw=data.tobytes();blob.extend(raw)
    vi=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw)})
    ac={'bufferView':vi,'componentType':5126,'count':len(data),'type':kind}
    if kind=='SCALAR':ac.update(min=[float(data.min())],max=[float(data.max())])
    ai=len(g['accessors']);g['accessors'].append(ac);return ai

time=add(np.arange(rows,dtype=float)[:,None]/30,'SCALAR');clip={'name':'Paladin-unarmed-hit-recoil' if action=='hit' else 'Paladin-unarmed-straight-punch','channels':[],'samplers':[]}
keys=set(tracks)|{(names[n],'rotation') for n in modified}|{(names['root'],'translation')}
for i,path in sorted(keys):
    values=np.array([p[i][path] for p in poses])
    clip['channels'].append({'sampler':len(clip['samplers']),'target':{'node':i,'path':path}})
    clip['samplers'].append({'input':time,'output':add(values,'VEC4' if path=='rotation' else 'VEC3'),'interpolation':'LINEAR'})
g['animations']=[clip];g['buffers'][0]['byteLength']=len(blob)
for key in ['meshes','skins','nodes','materials','images']:assert g[key]==original[key],key
for i in range(len(base)):
    for key in ['translation','rotation','scale']:
        assert np.array_equal(poses[0][i][key],base[i][key]) and np.array_equal(poses[-1][i][key],base[i][key])
text=json.dumps(g,separators=(',',':')).encode();text+=b' '*((-len(text))%4);blob.extend(b'\0'*((-len(blob))%4))
destination.parent.mkdir(parents=True,exist_ok=True);assert destination.resolve()!=source.resolve()
destination.write_bytes(struct.pack('<III',0x46546c67,2,28+len(text)+len(blob))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(blob),0x004e4942)+blob)
destination.with_suffix('.'+action+'.json').write_text(json.dumps({'action':action,'contact_frame_one_based':9 if action=='punch' else None,'frames':rows,'guard':guard,'strike':strike,'torso_yaw_radians':yaw,'hip_yaw_radians':hip_yaw,'weight_shift_metres':list(zip(weight_x,weight_y,weight_z)),'planted_ankle_targets':True,'geometry_bind_and_nodes_preserved':True,'idle_endpoints_exact':True,'wrist_trajectories':measure},indent=2))
print('Created',rows,'poses for',action,'; source idle unchanged')
