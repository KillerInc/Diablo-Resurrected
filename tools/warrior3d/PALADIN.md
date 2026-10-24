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

## Unarmed walk test

The user's `palm_walk_noweapon_anims.glb` supplies `palM_hth_nav_walk`:
40 samples at 30 fps, from 0 to 1.3 seconds, with 193 animated bones.
`merge_paladin_walk.py` matches bone names, parents and local rest matrices
(maximum difference 1.013e-5 for these exports). It appends animation buffer
data and remaps animation references without rewriting character mesh, skin
or node records. No generic retargeting is performed; incompatible rest poses
or missing bones are rejected.

`preview_paladin_walk.py` imports the merged GLB into Blender and renders all
40 frames from front, side and back. The preview camera follows horizontal
pelvis motion; the original animation data remains in the GLB. Sampled poses
at frames 1, 11, 21 and 31 were visually inspected: no major detached geometry
or tearing was seen. This is a walk preview, not exhaustive collision testing
or an in-game test. Game assets and preview renders remain local.

```text
python tools/warrior3d/merge_paladin_walk.py CHARACTER.glb WALK.glb OUTPUT.glb
blender -b --python tools/warrior3d/preview_paladin_walk.py -- OUTPUT.glb PREVIEW_DIRECTORY
```

## Installed unarmed town-walk sheet

On 2026-10-24, generated and installed only
`D:/Games/Diablo/HD/plrgfx/warrior/wln/wlnwl.png` (6144 x 6144 RGBA).
The user authorized overwriting installed sheets and retains backups elsewhere.

Pipeline:

1. `prepare_town_walk.py` measures the original WLNWL CL2 body masks (excluding
   palette-zero shadows), and extracts those shadows from the user's NN x8 PNG.
2. `render_paladin_town_walk.py` renders the merged walk at source frames
   1, 6, 11, 16, 21, 26, 31 and 36. Orthographic camera elevation is 30 degrees.
   Rotations produce S, SW, W, NW, N, NE, E, SE. Horizontal root travel is removed.
3. `assemble_paladin_town_walk.py` fits rendered alpha with one uniform scale
   and one fixed registration per direction, averaged over the whole cycle.
   Each body is composited over the corresponding unmodified vanilla shadow.
   All 64 cells were checked for clipping and sheet dimensions were verified.

Installed SHA256:
`BBA568A9A324B7F154CF41F2D8236C40F3431C3717F1242A692C0EFED8C8EA15`.

Live verification used the existing installed Diablo Reincarnated 0.4.0-pre
executable, isolated test saves/configuration, a new Warrior with weapon and
shield unequipped, and F10 HD mode. The log confirms `wlnwl.png` loaded as eight
directions / eight frames with 2x retained density. Movement was observed in
town, including scenery occlusion behind trees and the retained ground shadow.
GPU captures 8850, 12250-12450 and 13450-13650 contain the new walking character.
This is a limited directional walk test, not a full gameplay regression.

The initial pass replaced only town walking; the idle addition is recorded below.
There is no engine modification, executable replacement or build-version bump.

## Town idle addition and consistent action sampling

The user's `palm_Idle_anims.glb` contains `palM_HTH_nav_idle`: 80 samples over
2.6333 seconds, with the same 193 matching animated bones. The idle is merged
onto the edited model without modifying its meshes, skin or nodes.

The sheet pipeline now handles both eight-frame walk and twenty-frame idle
references. Blender's scene rate is set to 30 fps **before** glTF import so
animation times map to their original sample numbers. Idle samples are
0,4,...,76 and walk samples are 0,5,...,35 (zero-based Blender frame numbers).
The walk was regenerated to correct the earlier default-import-rate sampling.
Both actions use the original walk fit's identical pixel scale and eight
direction registrations; idle is not independently resized. All 160 idle cells
and all 64 corrected walk cells fit within their transparent canvases.

Installed town sheets:

| Sheet | Pixel dimensions | SHA256 |
| --- | --- | --- |
| `wlnst.png` | 6144 x 15360 | `E49DA41C00277DB56F2B98AAA4F16C9396776D15E87C0EC95F2CFA51F4B5D17D` |
| `wlnwl.png` | 6144 x 6144 | `7A674371F18094EA45D348F324F52DC5575FEE0E3131B80508023946C7699F3E` |

Live verification with the isolated unarmed Warrior confirmed both WLNST
(20 frames) and WLNWL (8 frames) load in the existing executable's HD renderer.
Standing, walking, and return to standing were observed. Stopping now retains
the Paladin appearance. The isolated game was saved with both weapon and shield
in inventory. Other equipment and dungeon animations remain vanilla/previous HD
assets. This does not establish complete collision or gameplay coverage.
