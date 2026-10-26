"""Preview the user's local weapons and shields without changing source assets.

Blender --python SCRIPT -- ASSET_DIRECTORY OUTPUT_DIRECTORY [MODEL.glb ...]
Renders front/back views at one fixed scale per equipment category.
No extracted artwork is embedded in this script or committed to Git.
"""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Matrix,Vector

args=sys.argv[sys.argv.index('--')+1:];source,out=map(Path,args[:2]);out.mkdir(parents=True,exist_ok=True)
assets=[('S1','sword_base00.glb','sword'),('S2','sword_base01.glb','sword'),('S3','sword_base03.glb','sword'),('H1','shield_base02.glb','shield'),('H2','shield_base04.glb','shield'),('H3','Shield_S15_Warrior.glb','shield')]
if len(args)>2:
    assets=[];counts={}
    for name in args[2:]:
        category=next((c for c in ['shield','sword','mace','axe','bow','staff'] if c in Path(name).name.lower()),'weapon');counts[category]=counts.get(category,0)+1;prefix={'shield':'H','sword':'S','mace':'M','axe':'A','bow':'B','staff':'T','weapon':'V'}[category];assets.append((f'{prefix}{counts[category]}',name,category))
report=[]
for label,name,category in assets:
    path=source/name;assert path.is_file(),path
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    meshes=[o for o in bpy.data.objects if o.type=='MESH'];assert meshes
    # Stand the raw D4 Z-axis model upright after Blender's glTF axis conversion.
    rotation=Matrix.Rotation(-math.pi/2,4,'X')
    for o in meshes:o.matrix_world=rotation@o.matrix_world
    corners=[o.matrix_world@Vector(v) for o in meshes for v in o.bound_box]
    lo=Vector([min(p[i] for p in corners) for i in range(3)]);hi=Vector([max(p[i] for p in corners) for i in range(3)]);center=(lo+hi)*.5
    for o in meshes:o.location-=center
    scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=512;scene.render.resolution_y=768;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.world.color=(.15,.15,.15);scene.view_settings.view_transform='AgX'
    for pos,energy,size in [((2,-4,4),450,4),((-3,-2,1),180,3),((0,3,3),350,3)]:
        bpy.ops.object.light_add(type='AREA',location=pos);lamp=bpy.context.object;lamp.data.energy=energy;lamp.data.size=size;lamp.rotation_euler=(-lamp.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=1.05 if category=='shield' else 1.65;scene.camera=camera
    for view,pos in [('front',(1.1,-5,1)),('back',(-1.1,5,1))]:
        camera.location=pos;camera.rotation_euler=(-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str((out/f'{label}-{view}.png').resolve());bpy.ops.render.render(write_still=True)
    report.append({'label':label,'filename':name,'category':category,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'native_dimensions':list(hi-lo),'mesh_objects':len(meshes),'model_scaled':False})
(out/'equipment-options.json').write_text(json.dumps(report,indent=2));print(f'Rendered {len(assets)} local equipment options, front and back; source assets unchanged')
