# Segmented Warrior repair

Run Blender 5.1 against the local 39-part segmented Warrior GLB:

```powershell
& $blender --background --factory-startup --python-exit-code 1 --python tools/warrior3d/segmented/repair_weights.py -- --input '<local-model.glb>' --out '<private-output-directory>'
```

The workflow preserves imported body joint locations and original rest geometry, repairs unrelated bone influences, binds rigid equipment, and adds two reconstructed underarm surfaces. Their endpoints copy exact positions and skin weights from the arm rim and torso. UV-split duplicate vertices are collapsed only for detecting true boundary edges. New underarm materials are subdued placeholders because the original images contain no texture coverage for the missing surfaces.

The pauldron uses its own `Pauldron_L_Control` bone, independent of the upper arm, with its pivot fixed at the inner edge beside the neck. Test poses rotate it around that hinge without any outward translation. Triangle-intersection checks against torso, arms, hands, neck/head pieces and the reconstructed joins increase hinge rotation until no intersections remain. This is a pose evaluation helper, not a live Blender constraint: new animations must call it or have the resulting control poses baked. It does not guarantee clearance for arbitrary future poses or surface containment without triangle intersections.

Validated on the supplied export:

- Controlled 65-degree shoulder, 25-degree elbow, 20-degree knee test: edges stretched over 3x reduced from 183 to 0; maximum existing-mesh stretch reduced from 12.08x to 2.005x. This metric excludes new underarm surfaces.
- Both underarm surface endpoint errors are below 0.00001 across all 16 sampled motion poses (observed maximum 0).
- All 19 pauldron clearance evaluations report zero intersections against the checked body surfaces.
- The editable Blender candidate retains optional sword/back shield objects hidden in their own collection. The GLB copy retains that equipment; Blender is authoritative for its visibility state.

Outputs include `Warrior-weight-repair.blend`, a GLB copy, renders and a numeric validation report. Source exports and installed game files are untouched. Models, textures and reference-derived renders remain local and are never committed. Only these source tools and documentation belong in Git.

Still a candidate: underarm surface shape/materials need visual refinement; the hands retain their original gripping pose, knee/boot joins require further review, the segmented textures are lower-resolution than the original 4K input, and no gameplay animation or sprite replacement has been accepted. The map is specific to this inspected 39-part export.

Hinge refinement: all 19 tested poses have zero measured hinge translation and zero detected body intersections. Clearance uses only 0-3 additional degrees of hinge rotation; there is no translational push away from the torso.
