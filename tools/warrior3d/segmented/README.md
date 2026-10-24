# Segmented Warrior refinement

Run Blender 5.1 against the local inspected 39-part segmented Warrior GLB:

```powershell
& $blender --background --factory-startup --python-exit-code 1 --python tools/warrior3d/segmented/repair_weights.py -- --input '<local-model.glb>' --out '<private-output-directory>'
& $blender --background '<private-output-directory>/Warrior-weight-repair.blend' --python-exit-code 1 --python tools/warrior3d/segmented/review_motion.py -- '<private-review-directory>'
```

The output is a separate editable candidate; original exports and the installed game are untouched. Third-party models, textures, Blender scenes and rendered diagnostics remain local. Only source tools, documentation and numeric validation belong in Git.

## Current refinement

- Remove unrelated bone influences and bind rigid equipment to inspected attachments.
- Replace flat underarm strips with closed rounded sockets. Concealed end rings follow chest and upper-arm bones exactly; dual-quaternion skinning preserves the rounded cross-section. The reconstructed surfaces use subdued materials, since there is no original texture coverage for their missing geometry. They overlap adjoining surfaces rather than welding the source topology.
- Bend knees around an armature-space mediolateral axis, independent of imported bone roll. Rebuild trouser knee weights as smooth monotonic thigh/calf transitions. Add patella controls with half-angle follow, and make the large left knee plate follow thigh, kneecap and calf regions.
- Preserve the approved inner-edge pauldron hinge. Its control rotates around a fixed point beside the neck with no translational push. Triangle-intersection checks add hinge rotation for clearance against nearby body surfaces.
- Render front, side and rear views across 16 samples, then bake a 17-frame review action with a duplicate loop endpoint into `Warrior-refinement-review.blend`.

## Validation and limits

The current exercise combines 65-degree shoulder abduction, 25-degree elbow motion and 60-degree knee flexion. Existing-mesh maximum edge stretch is approximately 1.88x, with zero edges over 3x; the 99th percentile is approximately 1.11x. This metric excludes the newly constructed shoulder sockets. Socket endpoint error is below 0.00001 across all sampled frames. The baked review loop's first/last bone matrix error is below 0.00001. All sampled pauldron checks have zero detected intersections and negligible fixed-hinge drift.

The clearance helper evaluates poses; it is not a live Blender collision constraint. Future animations must call it or bake its resulting control poses. Intersection tests do not establish absence of complete mesh containment, nor clearance in arbitrary untested poses. The numeric checks alone do not establish art quality.

The hand retains its original gripping shape. Socket surface texture blending, equipment seams and low-resolution segmented textures still need art review. This is a joint-range exercise, **not a walking animation**: the feet intentionally leave the ground. Locomotion requires separate foot planting, IK/balance and timing validation. No game sheets are accepted or installed.

## References supplied by the user

- [80.lv: human character movement simulation](https://80.lv/articles/next-gen-simulation-of-biped-character-movement-002sgr) and its [primary research project](https://mrl.snu.ac.kr/research/ProjectScalable/Page.htm): anatomical motion, joint limits and balanced locomotion. This workflow does not implement the paper's muscle-actuated reinforcement-learning simulation.
- [Academy of Animated Art: rigging terms](https://academyofanimatedart.com/master-these-important-3d-rigging-terms/): hierarchy, skin weights, FK/IK and deformation constraints.
- [SideFX Houdini 21 rigging](https://www.sidefx.com/products/whats-new-in-h21/rigging/): reusable controls, anatomical components and corrective deformation. Here the refinements are implemented in the existing Blender workflow; Houdini/APEX is not required or claimed to be implemented.

These are principles and quality references, not proof that this asset matches their demonstrated production quality.
