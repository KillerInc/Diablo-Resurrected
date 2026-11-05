"""Blender --background --python SCRIPT -- PRIVATE_OUTPUT
Build original leather sheath/hangers; no proprietary artwork is embedded.
"""
import bpy,sys,math
from pathlib import Path
out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(exist_ok=True,parents=True)
def material(name,color,metal=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=.78;return m
def box(name,center,size,mat,contact=False):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.dimensions=size;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);o.data.materials.append(mat);o['town_contact_ok']=contact;return o
def export(name):
 bpy.ops.export_scene.gltf(filepath=str((out/name).resolve()),export_format='GLB',use_selection=False,export_animations=False,export_extras=True)
bpy.ops.wm.read_factory_settings(use_empty=True);leather=material('Dark red sheath leather',(.28,.038,.024));edge=material('Leather edges',(.09,.021,.014));brass=material('Worn dark metal chape',(.22,.16,.085),.6);verts=[]
for y,w,d in [(-.055,.066,.028),(-.90,.052,.024),(-1.075,.015,.017)]:verts.extend([(-w,y,-d),(w,y,-d),(w,y,d),(-w,y,d)])
faces=[(0,3,2,1),(8,9,10,11)]
for row in range(2):
 for side in range(4):a=row*4+side;b=row*4+(side+1)%4;faces.append((a,b,b+4,a+4))
mesh=bpy.data.meshes.new('Closed leather sheath');mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new('Sword sheath',mesh);bpy.context.collection.objects.link(o);o.data.materials.append(leather)
box('Sheath collar',(0,-.095,0),(.144,.042,.069),edge);box('Sheath welt left',(-.054,-.46,.029),(.008,.73,.009),edge);box('Sheath welt right',(.054,-.46,.029),(.008,.73,.009),edge);box('Metal sheath tip',(0,-1.015,0),(.048,.11,.047),brass);box('Belt hanger sword',(0,.015,-.09),(.075,.28,.075),edge,True);export('TownSwordSheath.glb')
bpy.ops.wm.read_factory_settings(use_empty=True);leather=material('Mace belt frog',(.13,.045,.021));metal=material('Dull iron frog buckle',(.18,.16,.12),.55)
bpy.ops.mesh.primitive_torus_add(major_radius=.038,minor_radius=.009,major_segments=16,minor_segments=6,location=(0,.12,0),rotation=(math.pi/2,0,0));o=bpy.context.object;o.name='Mace leather retaining loop';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);o.data.materials.append(leather);box('Belt hanger mace',(-.07,.19,-.12),(.18,.16,.10),leather,True);box('Mace frog buckle',(0,.13,-.054),(.07,.04,.014),metal);export('TownMaceFrog.glb')
print('Created private original sheath and belt frog geometry')
