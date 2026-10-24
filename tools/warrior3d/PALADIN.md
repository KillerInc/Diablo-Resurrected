# Male Paladin candidate 1

`paladin_candidate.py` edits the user's private, skirt-free
`Paladin_M_outfit_D1_Candidate_1.glb` in Blender 5.1. It writes a separate
GLB, editable Blender scene, front/back/side previews and a validation report.
Game models, textures and rendered derivatives stay outside this repository.

```text
blender -b --python tools/warrior3d/paladin_candidate.py -- INPUT.glb OUTPUT_DIRECTORY
```

The input uses male Paladin base16 torso, base01 gloves/legs and base05 boots.
The user already removed the fur skirt. This pass:

- Reflects the shoulder/upper-arm assembly and associated skin to the opposite
  side, remapping left/right bone weights. Keeps its spikes and the original
  separate forearm/glove meshes.
- Adds a dark leather diagonal chest strap, back strap, edge details and buckle.
  Geometry follows the cuirass surface and receives its deformation weights.
- Removes the right-hip blade, sheath, hilt and dedicated attachment loops.
  Keeps the waist belt and remaining pockets.

Component selection is specific to this export. Vertex-count guards reject
obviously incompatible inputs; do not run it on a different outfit without
inspecting its mesh islands. An export with the same vertex counts can still
have different topology, so the guards are not a universal compatibility check.
The input is not overwritten.

## Validation on 2026-10-24

Front, back and side renders were inspected. The exported GLB retains all 750
source joints and 44 embedded texture images. Skin-weight sums differ from 1
by at most 1.2e-7. The forearm/glove geometry is unchanged. The source contains
no animation clips; animation deformation and in-game behavior have not been
validated. There is no engine build/version change in this asset-only pass.

## Earlier donor shortlist

The inspected male Paladin donor candidates were base09 Hide Tunic for light,
base01 Tunic for medium, and base05 Sand-Worn Vestment for heavy. The user's
mixed Candidate 1 supersedes the matching Hide set for the current light look.
Medium and heavy outfits are not yet finalized.
