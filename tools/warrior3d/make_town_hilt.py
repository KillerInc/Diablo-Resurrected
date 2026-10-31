"""Blender --python SCRIPT -- SOURCE_SWORD.glb NEW_PRIVATE_HILT.glb
Town-only handle/guard copy; remove the blade without changing the source.
"""
import bpy,bmesh,sys,json
from pathlib import Path
source,dest=map(Path,sys.argv[sys.argv.index('--')+1:]);assert source.is_file() and source.resolve()!=dest.resolve() and not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source.resolve()));counts=[]
for o in list(bpy.data.objects):
 if o.type!='MESH':continue
 bm=bmesh.new();bm.from_mesh(o.data);before=len(bm.faces);result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,-.035,0),plane_no=(0,1,0),clear_inner=True,clear_outer=False)
 edges=[e for e in result['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
 if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
 bm.to_mesh(o.data);bm.free();o.data.update();counts.append({'mesh':o.name,'faces_before':before,'faces_after':len(o.data.polygons)})
bpy.ops.export_scene.gltf(filepath=str(dest.resolve()),export_format='GLB',export_animations=False,export_extras=True)
dest.with_suffix('.fit.json').write_text(json.dumps({'source':str(source.resolve()),'town_hilt_only':True,'blade_cut_y':-.035,'meshes':counts},indent=2));print('Created private town handle and guard',counts)
