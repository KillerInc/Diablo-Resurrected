"""Bake native weapon orientation with an exact right-palm staff grip.
Blender --python SCRIPT -- MODEL.glb STAFF.glb OUTPUT.glb ROWS
"""
import bpy,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).parent))
from bake_bow_equipment import keys
def bake(model,source,dest,rows,grip_slide=0):
 bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(Path(model).resolve()));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(Path(source).resolve()));objects=[o for o in set(bpy.data.objects)-before if o.type=='MESH'];assert len(objects)==1;o=objects[0];raw=[o.matrix_world@v.co for v in o.data.vertices];poses=[]
 for row in range(rows):
  scene.frame_set(row);bpy.context.view_layer.update();hand=rig.matrix_world@rig.pose.bones['hand.R'].matrix;pose=rig.matrix_world@rig.pose.bones['weapon.R'].matrix@Matrix.Rotation(-math.pi/2,4,'Z')@Matrix.Scale(.8,4);left=rig.matrix_world@rig.pose.bones['hand.L'].matrix@Vector((0,.05,0));right=hand@Vector((.0425,.0825,-.002));grip_y=1.29-(left-right).length/.8+grip_slide;axis=(left-right).normalized();cross=pose.to_3x3().col[0];cross=(cross-axis*cross.dot(axis)).normalized();pose=Matrix((cross,axis,cross.cross(axis))).transposed().to_4x4()@Matrix.Scale(.8,4);pose.translation=hand@Vector((.0425,.0825,-.002))-pose@Vector((0,grip_y,0));local=hand.inverted()@pose;poses.append([local@v for v in raw])
 keys(o,poses);o.parent=None;o.matrix_world=Matrix.Identity(4);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);scene.frame_start=0;scene.frame_end=rows-1;scene.frame_set(0);bpy.ops.export_scene.gltf(filepath=str(Path(dest).resolve()),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='SCENE',export_anim_scene_split_object=False,export_frame_range=True,export_force_sampling=True)
if __name__=='__main__':
 a=sys.argv[sys.argv.index('--')+1:];bake(*a[:3],int(a[3]))
