"""Transfer named local rest-pose deltas; retain all Paladin geometry and bind data.

python retarget_paladin_kick.py CHARACTER.glb ANIMATION.glb OUTPUT.glb
Class-specific numbered muscle tracks are excluded; matching named tracks require
the same parent. Output remains a preview candidate pending visual inspection.
"""
import copy,json,re,struct,sys
from pathlib import Path
import numpy as np
from merge_paladin_walk import read

def mul(a,b):
    av,aw=a[...,:3],a[...,3:];bv,bw=b[...,:3],b[...,3:]
    return np.concatenate((aw*bv+bw*av+np.cross(av,bv),aw*bw-np.sum(av*bv,axis=-1,keepdims=True)),axis=-1)

def inv(q):
    r=q.copy();r[...,:3]*=-1
    return r/np.sum(q*q,axis=-1,keepdims=True)

def main(character,animation,destination):
    c,cb=read(character);a,ab=read(animation);original=copy.deepcopy(c)
    assert not c.get('animations')
    cn={n.get('name'):i for i,n in enumerate(c['nodes'])}
    ap={ch:i for i,n in enumerate(a['nodes']) for ch in n.get('children',[])}
    cp={ch:i for i,n in enumerate(c['nodes']) for ch in n.get('children',[])}
    mapping={i:cn[n['name']] for i,n in enumerate(a['nodes']) if n.get('name') in cn and not re.fullmatch(r'm\d+\.[LR]',n['name']) and n['name']!='uiAnimated'}
    # Class-specific clavicle helpers have different numbered names. Match
    # ancestor chains of known semantic joints, never arbitrary numeric IDs.
    bridges={}
    for i,j in list(mapping.items()):
        while i in ap and j in cp:
            i,j=ap[i],cp[j];sn=a['nodes'][i]['name'];tn=c['nodes'][j]['name']
            if i in mapping:assert mapping[i]==j,('ancestor conflict',sn);break
            assert sn==tn or (re.fullmatch(r'm\d+\.[LR]',sn) and re.fullmatch(r'm\d+\.[LR]',tn)),('incompatible ancestor',sn,tn)
            mapping[i]=j;bridges[sn]=tn
    blob=bytearray(cb);c['animations']=[];skipped=set();matched=set()
    def values(index):
        ac=a['accessors'][index];v=a['bufferViews'][ac['bufferView']]
        assert ac['componentType']==5126 and 'byteStride' not in v and 'sparse' not in ac
        width={'SCALAR':1,'VEC3':3,'VEC4':4}[ac['type']]
        return np.frombuffer(ab,dtype='<f4',count=ac['count']*width,offset=v.get('byteOffset',0)+ac.get('byteOffset',0)).reshape(-1,width).copy()
    def add(data,kind):
        data=np.asarray(data,dtype='<f4');blob.extend(b'\0'*((-len(blob))%4));offset=len(blob);raw=data.tobytes();blob.extend(raw)
        vi=len(c['bufferViews']);c['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw)})
        ac={'bufferView':vi,'componentType':5126,'count':len(data),'type':kind}
        if kind=='SCALAR':ac.update(min=[float(data.min())],max=[float(data.max())])
        ai=len(c['accessors']);c['accessors'].append(ac);return ai
    for clip in a['animations']:
        new={'name':clip.get('name','kick')+'-Paladin','channels':[],'samplers':[]}
        for ch in clip['channels']:
            i=ch['target']['node'];sn=a['nodes'][i];name=sn['name']
            if i not in mapping:skipped.add(name);continue
            j=mapping[i];tn=c['nodes'][j]
            if i in ap:
                assert j in cp and mapping.get(ap[i])==cp[j],('parent mismatch',name)
            matched.add(name);path=ch['target']['path'];sm=clip['samplers'][ch['sampler']]
            assert sm.get('interpolation','LINEAR')=='LINEAR'
            data=values(sm['output'])
            if path=='rotation':
                sr=np.array(sn.get('rotation',[0,0,0,1]));tr=np.array(tn.get('rotation',[0,0,0,1]))
                data=mul(mul(tr,inv(sr)),data);data/=np.linalg.norm(data,axis=1,keepdims=True)
            elif path=='translation':
                st=np.array(sn.get('translation',[0,0,0]));tt=np.array(tn.get('translation',[0,0,0]))
                # Keep Paladin bone lengths; preserve animated displacement only.
                ratio=np.linalg.norm(tt)/np.linalg.norm(st) if np.linalg.norm(st)>.05 else 1
                data=tt+(data-st)*ratio
            elif path=='scale':
                data=data/np.array(sn.get('scale',[1,1,1]))*np.array(tn.get('scale',[1,1,1]))
            else:raise ValueError(path)
            ns={'input':add(values(sm['input']),'SCALAR'),'output':add(data,'VEC4' if path=='rotation' else 'VEC3'),'interpolation':'LINEAR'}
            new['channels'].append({'sampler':len(new['samplers']),'target':{'node':j,'path':path}});new['samplers'].append(ns)
        c['animations'].append(new)
    required={'root','attach','center','chest','pelvis','head'}|{n+s for n in ['upperArm','forearm','hand','thigh','shin','ankle','foot'] for s in ['.L','.R']}
    assert required<=matched,required-matched
    for k in ['nodes','meshes','skins','materials','images']:assert c.get(k)==original.get(k),k
    c['buffers'][0]['byteLength']=len(blob);text=json.dumps(c,separators=(',',':')).encode();text+=b' '*((-len(text))%4);blob.extend(b'\0'*((-len(blob))%4))
    dest=Path(destination);dest.parent.mkdir(parents=True,exist_ok=True);assert dest.resolve()!=Path(character).resolve()
    dest.write_bytes(struct.pack('<III',0x46546c67,2,28+len(text)+len(blob))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(blob),0x004e4942)+blob)
    report={'matched_named_bones':sorted(matched),'ancestor_bridges':bridges,'skipped_class_specific_tracks':sorted(skipped),'geometry_bind_and_materials_unchanged':True,'method':'target rest rotation * inverse source rest rotation * source animation; preserve target bone translations'}
    dest.with_suffix('.retarget.json').write_text(json.dumps(report,indent=2));print('Retargeted',len(matched),'named bones; skipped',len(skipped))

if __name__=='__main__':main(*sys.argv[1:4])
