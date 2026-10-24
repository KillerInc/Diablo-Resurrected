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

## Shadow alignment and darker palette pass

The user reported that the reused vanilla idle shadow did not fit the new
stance, and the sprite was too bright for Diablo. The current sheets supersede
the prior shadow/color output above:

- `render_paladin_shadows.py` projects each animated pose onto the z=0 ground
  plane, with the same camera, pose and root-motion correction as its body.
  It uses opaque head, torso, limb and armor geometry; transparent hair cards,
  facial overlays and eye planes do not cast silhouette artifacts.
- The assembler transforms each projected shadow with the body's identical
  scale and registration. A two-pixel edge blur and 70% opacity replace the
  copied original shadow. Both idle and walk now use model-matched shadows.
- Body RGB is multiplied by 0.62 and saturation is reduced to 0.86, preserving
  alpha and the existing geometric alignment. This is a deliberate darker art
  pass; source textures and raw body renders are unchanged.

The eight-direction contact sheets were visually reviewed and all 224 body
cells remain uncropped. The updated PNGs were installed and hashes verified.
This latest art pass has offline visual validation; the live checks above
refer to the earlier palette/shadows. Restart the game to clear its sheet cache.

Current installed hashes:

- WLNST: `A5BE20632726DEEE258ECE4800C8CA94BCBD6FFCE07C44083B146A41A21A21C4`
- WLNWL: `87725C4BD0E885F361FEB001D970EB3DF4B4611005319C51571649E1765BCF39`

To use projected shadows, pass their output directory as a fifth positional
argument after the calibration JSON to `assemble_paladin_town_walk.py`:

```text
blender -b --python tools/warrior3d/render_paladin_shadows.py -- RENDER.blend render.json SHADOW_DIRECTORY
python tools/warrior3d/assemble_paladin_town_walk.py FRAMES REFERENCE OUTPUT CALIBRATION.json SHADOW_DIRECTORY
```

## Shorter stride

The user requested shorter steps while retaining the grid-based tile duration.
`shorten_paladin_stride.py` edits the source animation buffers directly:
thigh/shin/foot rotations blend 60% toward each bone's cycle mean, while pelvis
translation excursion is halved. Mesh buffers, joint hierarchy, inverse bind
matrices, skin weights, texture data and sample times are preserved. A Blender
re-export approach was rejected after its rendered legs distorted; only the
direct-buffer result was installed.

`measure_paladin_stride.py` evaluates every pose's boot geometry. Its measured
ground offset is applied to the root translation so one boot maintains ground
contact without changing the waist/chest joint relationship. Final minimum
boot height across 40 poses is 0.00299988â€“0.00300016 metres (target 0.003).
Forward foot excursion falls from approximately 1.117 / 1.084 metres to
0.695 / 0.709 metres: about 36% shorter on average. All eight views were rendered
and the 64 output cells validated without clipping. Shadows were regenerated
from this motion, using the existing darker palette and fixed camera calibration.

Installed WLNWL SHA256:
`BBC37C30440EE22C5BE2977B39A4EA4191E1BECBAA9DA94ECE0B3C0BEFAFDC90`.
Idle remains unchanged. The stride-comparison GIF plays both versions at
50 ms per frame (the normal eight-frame cycle); earlier slow art previews are
not playback-speed references. No engine timing or movement-speed changes were
made. This pass is render/geometry validated; live gameplay feel remains to judge.

## Approved walk and unarmed dungeon coverage

The user subsequently tested the shorter town walk in game and approved its
appearance. It is the baseline for further animation work.

`prepare_paladin_dungeon.py` reuses that approved walk for `wlnaw.png` (eight
frames) and every second rendered town-idle pose for `wlnas.png` (ten frames).
Both layouts were checked against the original NN8 PNG and extracted CL2 frame
counts. The existing scale, fixed directional registration, palette and matching
projected shadows are retained. All 144 dungeon body cells passed crop checks;
eight-direction contact sheets were visually reviewed. Installed hashes match:

- WLNAW: `BBC37C30440EE22C5BE2977B39A4EA4191E1BECBAA9DA94ECE0B3C0BEFAFDC90`
- WLNAS: `F381CFDA8A7326FF6650CCAB1A5E6EF8DC655F688782546D3D29A2AA350EDF5C`

Dungeon standing currently uses the relaxed idle, pending a suitable combat-ready
clip. Dungeon use has offline validation only. No engine or executable changes
were needed. Preview timing now follows normal 20 Hz engine ticks: 50 ms for
walking and 200 ms for standing (four ticks per frame).

The user's unarmed suffix mapping is AS dungeon standing, AW dungeon walking,
ST town standing, WL town walking, AT attack, HT hit reaction, BL blocking,
DT death, FM fire casting, LM lightning casting and QM other magic casting.
Only AS/AW/ST/WL have Paladin replacements. Other action sheets remain existing
artwork. The inspected animation exports contain only `palM_HTH_nav_idle` and
`palM_hth_nav_walk`; `palm_anims.glb` duplicates the idle clip. The next needed
export is an unarmed attack on this same Paladin skeleton. Hit, block, death and
casting clips are also needed for complete action coverage. No missing motion
is represented as already available or complete.

## Barbarian kick transferred to Paladin unarmed attack

The user supplied `palm_kick_anims.glb`, containing `barM_DW_attk_kick`
(42 samples, 1.3667 seconds). Direct merging correctly rejected its different
rest transforms. `retarget_paladin_kick.py` instead transfers local animation
deltas to the Paladin's rest pose, retaining target bone lengths, mesh buffers,
nodes, skin bindings, materials and textures. It transfers 49 bone tracks and
skips 139 class-specific tracks. Numbered clavicle ancestors are matched through
known upper-arm parent chains, not by coincidental numeric names. This is an
art-tested transfer, not a general-purpose retargeter for all D4 classes.

`sample_paladin_kick.py` samples sixteen poses, with source sample 8 on sheet
row 8 (zero based). Warrior data specifies unarmed action frame 9; `DoAttack`
checks `currentFrame == _pAFNum - 1`, so the visible contact pose aligns with
damage processing. At normal speed the sixteen-frame attack lasts 0.8 seconds.
First and last poses blend to the current idle. Full Barbarian extension exceeded
the original cell width in east/west views; a 0.70 motion blend produces a more
compact kick without rescaling the character. This gain is an animation blend,
not a literal 30% reduction in measured foot travel.

`measure_paladin_attack.py` evaluates boot geometry and supporting-foot position.
The sampler's optional measurement input corrects root translation, locking the
left foot horizontally and grounding the boots. Final sixteen-pose boot minimum
Z is 0.002999946â€“0.003000137 metres; supporting-foot XY drift is below 1.2e-7 m.
Horizontal pelvis tracking is disabled for this action so the supporting foot
stays planted while the body leans. Shadows follow exactly the same poses.
The full projected attack shadow exceeded the cell's bottom edge. This action
uses a deliberately compact contact shadow: projected ground coordinates retain
20% of their distance from the planted left foot before rendering. This is an art
adjustment, not a physically exact directional shadow. Walking and idle retain
their existing shadow projection. The assembler checks attack shadow bounds as
well as body bounds to reject hard sheet-edge cutoffs.

AT has 128-pixel logical cells, unlike the 96-pixel standing/walking cells.
The reference decoder, renderer and assembler now accept this larger layout.
Rendering preserves pixels per metre; composition preserves horizontal center
and bottom registration relative to the approved walk calibration. No character
rescaling or engine changes are involved. Reassembling the existing AW sheet
through the generalized pipeline reproduced its SHA256 exactly.

All 128 attack cells passed raw and assembled crop checks. Contact poses in all
eight directions were visually reviewed. The installed sheet is 8192 x 16384
RGBA, SHA256 `BE19170424D81188E1D895C794FE3628F0C2E87EB4C8D1B6B30E34B3595A6868`.
Local assets and the full-cell, three-view `attack-preview.gif` are under the
edited candidate's `Unarmed Kick` directory. Only WLNAT was installed in this
pass; the approved walk/idle sheets remain intact. In-game kick feel and actual
hit contact still need gameplay verification. Restart to reload cached sheets.

Reproduction order (all artwork inputs and outputs remain outside Git):

1. Retarget the edited static character and supplied kick with
   `retarget_paladin_kick.py`.
2. Run `sample_paladin_kick.py RETARGET IDLE SAMPLED` and evaluate SAMPLED with
   Blender's `measure_paladin_attack.py`.
3. Run `sample_paladin_kick.py RETARGET IDLE FINAL MEASUREMENT.json`, then measure
   FINAL to verify ground contact.
4. Prepare the original WLNAT PNG/CL2 using `prepare_town_walk.py`. In its local
   reference JSON set `source_frames` to 0 through 15 and
   `preserve_horizontal_root_motion` to true and `shadow_distance_gain` to 0.20.
5. Render FINAL with `render_paladin_town_walk.py`, project matching shadows with
   `render_paladin_shadows.py`, and assemble with the original walk calibration
   using `assemble_paladin_town_walk.py`.

The Paladin coverage is now AS/AW/ST/WL/AT. Hit, block, death and casting clips
remain outstanding; their sheets still use the existing artwork.

## Kick shadow correction and height audit

The user rejected the compact kick shadow. The 0.20 projection-distance gain
above made it too small; passing crop checks did not establish visual suitability.
The installed replacement uses `reuse_paladin_idle_shadow.py` to hold the approved
idle frame-zero ground shadow at its existing size/direction through all sixteen
attack frames. This is deliberately a stable shadow approximation: it does not
cast the raised kicking leg. It supersedes the compact projected attack shadow.
All 128 body and shadow bounds pass; body bounds are identical to the previous
kick sheet. Use the shadow reuse helper after rendering, in place of step 5's
attack-shadow projection, then pass its output directory to the assembler.

Height was audited against the edited static GLB and current idle. Mesh, skin,
node and material records are identical, and both actions use pixel scale
1.1334110707181562. After removing the attack cell's padding, the starting-pose
body height matches idle within one 8x-sheet pixel in all eight directions.
The grounding correction shifts that pose about 2–3 sheet pixels upward; it does
not increase model height. Pose changes during the kick alter the silhouette.
The correction changes only the shadow, retaining that body placement.

Current WLNAT SHA256:
`9106FFB8BF4BF9B7AE128C10A31C05572F3D7730C30942748D90B4A0F168EBB5`.
Local `height-audit.json` records per-direction measurements. The uniquely named
`attack-preview-shadow-fixed.gif` shows the replacement without preview-cache
ambiguity. Gameplay verification of this shadow revision remains outstanding.
