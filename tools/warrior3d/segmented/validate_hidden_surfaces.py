"""Validate the generated closed back/neck/head geometry in the review scene."""
import bpy,json,sys
from pathlib import Path
from collections import Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');result={}
for o in bpy.data.objects:
    if o.type!='MESH' or not o.name.startswith('Reconstructed '):continue
    counts=Counter(tuple(sorted(pair)) for face in o.data.polygons for pair in face.edge_keys)
    assert all(n==2 for n in counts.values()),(o.name,'open surface')
    tree=BVHTree.FromPolygons([v.co for v in o.data.vertices],[tuple(f.vertices) for f in o.data.polygons])
    samples=[(.014,.66),(.014,.72),(.014,.765)] if 'torso' in o.name else ([(.013,.82)] if 'neck' in o.name else [(.007,.90)])
    for x,z in samples:
        location,normal,index,distance=tree.ray_cast(Vector((x,.3,z)),Vector((0,-1,0)))
        assert location is not None,(o.name,'back ray missed',x,z)
    result[o.name]={'closed_manifold_edges':True,'back_rays_hit':len(samples)}
assert len(result)==3
Path(sys.argv[sys.argv.index('--')+1]).write_text(json.dumps(result,indent=2))
print('CLOSURE_VALIDATION',json.dumps(result),flush=True)
