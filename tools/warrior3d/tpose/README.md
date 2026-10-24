# T-pose Warrior trial and repair

Asset-specific workflow for the inspected 50-part `D1+Warrior+T-Pose.glb`. Requires Blender 5.1 with its bundled NumPy and glTF importer/exporter. Original assets and generated models/renders stay local and must not be committed.

```powershell
& $blender --background --factory-startup --python-exit-code 1 --python tools/warrior3d/tpose/test_repair.py -- --input '<local-T-pose.glb>' --out '<private-output>'
& $blender --background '<private-output>/Warrior-T-Pose-animated.blend' --python-exit-code 1 --python tools/warrior3d/tpose/validate_scene.py -- '<private-output>/saved-scene-validation.json'
& $blender --background '<private-output>/Warrior-T-Pose-animated.blend' --python-exit-code 1 --python tools/warrior3d/tpose/export_visible.py -- '<private-output>/Warrior-T-Pose-repaired.glb'
```

## Inspected issues and fixes

- Shield had upper-arm/shoulder influences: bind to Spine2 and hide reversibly.
- Collar, back strap, waist hardware and bracer pieces had inappropriate cross-part influences: restrict or rigidly rebind inspected equipment. Preserve original relevant chest/shoulder influences in actual skin; do not reuse the previous asset's torso patch map.
- Upper-arm mail carried forearm weights: transfer those to the upper arm; bind its cuff rigidly to the upper arm.
- Metal pauldron was fused with the coat: separate the inspected upper-left metal region (283 faces) while preserving source vertices, material and UV positions. Retain the hidden source coat geometry. Add an independent fixed inner-edge hinge; resolve clearance by rotation only, with no translation. Validate against nearby shoulder, chest, neck and coat meshes.
- Smooth the right trouser knee's thigh/calf transition, keep rigid straps and plates on appropriate segments, and enable volume-preserving skin deformation.
- The visible unshielded back looks complete in the front/side/back review; no synthetic back panel is added to this model.

## Delivered local outputs

`Warrior-T-Pose-working.blend`: editable relaxed-pose candidate. `Warrior-T-Pose-animated.blend`: baked 17-frame joint-range action with a duplicate loop endpoint. `Warrior-T-Pose-repaired.glb`: visible character, 66-joint rig and the review action, excluding shield and hidden source-coat backup. Original export remains unchanged.

The script renders 16 front/side/back samples, before/after stills, and writes numeric validation. Joint exercise: arms lower 70 degrees from the source T-pose and return; elbows flex 20 degrees and knees 55 degrees. This is **not locomotion**: feet are intentionally unplanted. No game sheets or executable are installed or changed.

Validation on this input: original relaxed-arm pose had 10 mesh edges stretched over 3x (maximum about 5.10x); repaired visible geometry has zero over 3x (maximum about 1.97x). Bent-pose repaired maximum is about 1.93x with zero edges over 3x. The original metrics cover all originally visible pieces; repaired metrics cover the visible corrected pieces, including split coat/plate and excluding hidden originals. All 20 sampled hinge-clearance evaluations report zero triangle intersections and hinge drift below 0.000001. Saved bone matrices match at first/last loop frames. Portable GLB has one review animation and 66 skin joints.

Limits: geometric pauldron extraction is specific to this export. Triangle intersection tests do not prove clearance in arbitrary untested poses or detect all containment cases. Equipment seams, fingers, material fidelity and full gameplay motions still require visual review. This is a tested repair candidate, not a complete Warrior animation set. Reference artwork, imported geometry/textures, and rendered previews remain outside Git.
