"""Blender-only pose steering shared by body and projected-shadow rendering.

Redirect pelvis motion relative to its first pose, rather than yawing the actor
or translating the finished corpse. Preserve native child animation and solve
both legs to redirected native ankle trajectories. No artwork is embedded.
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
        self.reach_errors = []
        self.sample(first_frame)

    def sample(self, frame):
        # Restore basis explicitly: repeated frames must not inherit corrections.
        assert frame in self.native, ('Uncached native pose', frame)
        for name, matrix in self.native[frame].items():
            self.rig.pose.bones[name].matrix_basis = matrix
        bpy.context.view_layer.update()

    def rotation(self, name, quaternion):
        bone = self.rig.pose.bones[name]
        position, _, scale = bone.matrix.decompose()
        bone.matrix = Matrix.LocRotScale(position, quaternion, scale)
        bpy.context.view_layer.update()

    def apply(self, frame, angle):
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
        bones['attach'].matrix = corrected @ native['pelvis'].inverted() @ native['attach']
        bpy.context.view_layer.update()
        errors = []
        # Remove the native pair's common foot drift, not the body's travel.
        # The stance may fold/release, but its midpoint stays at the tile origin.
        drift = sum((native['ankle.'+s].translation - self.initial['ankle.'+s].translation
                     for s in ['L', 'R']), Vector()) * .5
        drift.z = 0
        for side in ['L', 'R']:
            thigh, shin, ankle = [n + '.' + side for n in ['thigh', 'shin', 'ankle']]
            target = self.initial[ankle].translation + steer @ (
                native[ankle].translation - self.initial[ankle].translation - drift)
            hint = self.initial[shin].translation + steer @ (
                native[shin].translation - self.initial[shin].translation)
            hip, knee, foot = [bones[n].matrix.translation.copy() for n in [thigh, shin, ankle]]
            a, b = (knee - hip).length, (foot - knee).length
            line = target - hip
            distance = max(abs(a-b)+1e-5, min(line.length, a+b-1e-5))
            direction = line.normalized()
            reachable = hip + direction * distance
            pole = hint - hip
            pole -= direction * pole.dot(direction)
            if pole.length < 1e-6:
                pole = Vector((0, -1, 0)).cross(direction)
            pole.normalize()
            along = (a*a-b*b+distance*distance)/(2*distance)
            desired_knee = hip + direction*along + pole*math.sqrt(max(0, a*a-along*along))
            self.rotation(thigh, (knee-hip).rotation_difference(desired_knee-hip) @ bones[thigh].matrix.to_quaternion())
            knee, foot = [bones[n].matrix.translation.copy() for n in [shin, ankle]]
            self.rotation(shin, (foot-knee).rotation_difference(reachable-knee) @ bones[shin].matrix.to_quaternion())
            first_rotation = self.initial[ankle].to_quaternion()
            delta = native[ankle].to_quaternion() @ first_rotation.inverted()
            self.rotation(ankle, steer @ delta @ steer.inverted() @ first_rotation)
            errors.append((bones[ankle].matrix.translation-target).length)
        self.reach_errors.append(max(errors))
        return max(errors)
