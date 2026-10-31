"""Blender-only pose steering shared by body and projected-shadow rendering.

Redirect the fall axis while preserving native joint poses. Anchor the horizontal
stance midpoint through the shared motion parent. No artwork is embedded.
"""
import math
import bpy
from mathutils import Matrix, Quaternion, Vector


class RedirectFall:
    def __init__(self, rig, first_frame=0):
        self.rig = rig
        rig.location = (0, 0, 0)
        rig.rotation_euler = (0, 0, 0)
        bpy.context.scene.frame_set(first_frame)
        bpy.context.view_layer.update()
        self.initial = {b.name: b.matrix.copy() for b in rig.pose.bones}
        self.action = rig.animation_data.action
        self.native = {}
        # Render-time dependency updates otherwise evaluate the original action
        # over the corrected pose. Cache it first, then suspend its evaluation.
        first, last = self.action.frame_range
        for frame in range(int(round(first)), int(round(last))+1):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            self.native[frame] = {b.name: b.matrix_basis.copy() for b in rig.pose.bones}
        rig.animation_data.action = None
        self.anchor_errors = []
        self.sample(first_frame)

    def sample(self, frame):
        # Restore basis explicitly: repeated frames must not inherit corrections.
        assert frame in self.native, ('Uncached native pose', frame)
        for name, matrix in self.native[frame].items():
            self.rig.pose.bones[name].matrix_basis = matrix
        bpy.context.view_layer.update()

    def apply(self, frame, angle, mode='pelvis'):
        self.sample(frame)
        bones = self.rig.pose.bones
        native = {b.name: b.matrix.copy() for b in bones}
        steer = Quaternion((0, 0, 1), angle)
        pelvis = bones['pelvis']
        first = self.initial['pelvis']
        position, rotation, scale = native['pelvis'].decompose()
        delta = rotation @ first.to_quaternion().inverted()
        position = first.translation + steer @ (position - first.translation)
        rotation = steer @ delta @ steer.inverted() @ first.to_quaternion()
        # Torso and pelvis are siblings under attach in this skeleton. Apply
        # the pelvis correction to their common parent, preserving their seam.
        corrected = Matrix.LocRotScale(position, rotation, scale)
        if mode == 'body_axis':
            first_mid = sum((self.initial['ankle.'+s].translation for s in ['L','R']), Vector())*.5
            current_mid = sum((native['ankle.'+s].translation for s in ['L','R']), Vector())*.5
            up = (self.initial['head'].translation-first_mid).normalized()
            axis = (native['head'].translation-current_mid).normalized()
            target = Quaternion(up, angle) @ axis
            turn = axis.rotation_difference(target)
            pivot = Vector((first_mid.x, first_mid.y, current_mid.z))
            transform = Matrix.Translation(pivot) @ turn.to_matrix().to_4x4() @ Matrix.Translation(-current_mid)
            bones['attach'].matrix = transform @ native['attach']
        else:
            assert mode == 'pelvis', mode
            bones['attach'].matrix = corrected @ native['pelvis'].inverted() @ native['attach']
        bpy.context.view_layer.update()
        # Preserve every native joint angle. Pin only the horizontal midpoint
        # of the stance through the shared motion parent; solving each ankle
        # separately can force inward knees as the pelvis turns during a fall.
        first_midpoint = sum((self.initial['ankle.'+side].translation
                              for side in ['L', 'R']), Vector()) * .5
        midpoint = sum((bones['ankle.'+side].matrix.translation
                        for side in ['L', 'R']), Vector()) * .5
        shift = first_midpoint - midpoint
        shift.z = 0
        attach = bones['attach'].matrix.copy()
        attach.translation += shift
        bones['attach'].matrix = attach
        bpy.context.view_layer.update()
        # Root motion may change; anatomical joint poses must remain native.
        for side in ['L', 'R']:
            for joint in ['thigh', 'shin', 'ankle', 'foot']:
                name = joint + '.' + side
                original = self.native[frame][name]
                actual = bones[name].matrix_basis
                assert max(abs(original[i][j]-actual[i][j])
                           for i in range(4) for j in range(4)) < 1e-5, ('Changed native leg pose', frame, name)
        midpoint = sum((bones['ankle.'+side].matrix.translation
                        for side in ['L', 'R']), Vector()) * .5
        error = math.hypot(midpoint.x-first_midpoint.x, midpoint.y-first_midpoint.y)
        self.anchor_errors.append(error)
        return error
