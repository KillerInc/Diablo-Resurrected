"""Author a separate 16-pose straight punch from the current idle's skeleton.

Blender --python SCRIPT -- IDLE.glb OUTPUT.glb
Two-bone arm IK is solved in glTF world coordinates. Only local rotations change;
all original geometry, skin bindings and node records are preserved. No glTF
scene re-export is used. This is a preview candidate, not an installed action.
"""
import copy,json,math,struct,sys
from pathlib import Path
import numpy as np
from mathutils import Matrix,Quaternion,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from merge_paladin_walk import read

source,destination=map(Path,sys.argv[sys.argv.index('--')+1:])
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

guard=[0,.15,.4,.7,1,1,1,1,1,1,1,1,.85,.6,.3,0]
strike=[0,0,0,0,.05,.15,.4,.75,1,.55,.2,0,0,0,0,0]
yaw=[0,0,-.02,-.06,-.10,-.08,-.03,.04,.13,.07,.01,-.02,-.01,0,0,0]
poses=[];measure=[];modified={'chest','upperArm.R','forearm.R','upperArm.L','forearm.L','hand.R','hand.L','head'}
modified|={f'm{number:03d}.{side}' for number in range(14,26) for side in ['R','L'] if f'm{number:03d}.{side}' in names}
for row in range(16):
    pose=copy.deepcopy(base)
    if guard[row]:
        chest=Quaternion((0,1,0),yaw[row])@Quaternion((1,0,0),.035*strike[row])@initial[names['chest']].to_quaternion()
        set_world_rotation(pose,'chest',chest)
        set_world_rotation(pose,'head',initial[names['head']].to_quaternion())
        world=world_matrices(pose)
        for side in ['R','L']:
            shoulder=position(world,'upperArm.'+side);sign=-1 if side=='R' else 1
            ready=Vector((sign*.23,1.30,.24))
            target=ready
            if side=='R':target=ready.lerp(shoulder+Vector((.035,-.055,.52)),strike[row])
            target=position(initial,'hand.'+side).lerp(target,guard[row])
            arm(pose,side,target,guard[row])
            world=world_matrices(pose)
            wrist=position(world,'hand.'+side);knuckles=position(world,'handEnd.'+side)
            forearm=wrist-position(world,'forearm.'+side)
            original_hand=world[names['hand.'+side]].to_quaternion()
            straight=(knuckles-wrist).rotation_difference(forearm)@original_hand
            set_world_rotation(pose,'hand.'+side,original_hand.slerp(straight,guard[row]))
            world=world_matrices(pose)
            lateral=world[names['handEnd.'+side]].to_3x3().col[2].normalized()
            # Four finger chains fold into a fist; preserve the source thumb.
            for first in [14,17,20,23]:
                for joint,degrees in enumerate([50,70,40]):
                    finger=f'm{first+joint:03d}.{side}'
                    if finger not in names:continue
                    world=world_matrices(pose)
                    bend=Quaternion(lateral,math.radians(degrees)*guard[row]*(-1 if side=='R' else 1))
                    set_world_rotation(pose,finger,bend@world[names[finger]].to_quaternion())
    world=world_matrices(pose)
    measure.append({'row':row,'right_wrist':list(position(world,'hand.R')),'left_wrist':list(position(world,'hand.L')),'right_elbow':list(position(world,'forearm.R')),'right_shoulder':list(position(world,'upperArm.R'))})
    poses.append(pose)

def add(data,kind):
    data=np.asarray(data,dtype='<f4');blob.extend(b'\0'*((-len(blob))%4));offset=len(blob);raw=data.tobytes();blob.extend(raw)
    vi=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw)})
    ac={'bufferView':vi,'componentType':5126,'count':len(data),'type':kind}
    if kind=='SCALAR':ac.update(min=[float(data.min())],max=[float(data.max())])
    ai=len(g['accessors']);g['accessors'].append(ac);return ai

time=add(np.arange(16,dtype=float)[:,None]/30,'SCALAR');clip={'name':'Paladin-unarmed-straight-punch','channels':[],'samplers':[]}
keys=set(tracks)|{(names[n],'rotation') for n in modified}
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
destination.with_suffix('.punch.json').write_text(json.dumps({'contact_frame_one_based':9,'frames':16,'guard':guard,'strike':strike,'torso_yaw_radians':yaw,'geometry_bind_and_nodes_preserved':True,'idle_endpoints_exact':True,'wrist_trajectories':measure},indent=2))
print('Created sixteen-pose straight punch; knee and idle input unchanged')
