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

## Project-wide lighting direction — user requirement

The user approved the southeast-sun preview and explicitly requires **all shadows
to follow that direction**: sun southeast, cast shadows northwest, consistently
across every character, facing direction and animation. Body lighting must agree
with the shadow. Using the established sprite direction convention, the preview
places the main light at Blender (3, -4, 6) and projects away from it toward
negative X / positive Y. Character rotation must not rotate the world light.

The review is local at `paladin-kick/sun-se-preview/sun-se-moving-shadow.gif`.
It shows the full moving shadow and original kick extension with cell boundaries.
It is approved for light direction, not a completed clipping solution. Installed
sheets have not yet been updated to this lighting: the prior held-idle kick shadow
is still installed, and idle/walk still have the earlier projection. Those need
consistent relighting in the next implementation pass. Do not treat the old
negative-X/negative-Y projection, compressed kick shadow or held idle shadow as
the final lighting standard.

## Knee attack review replacing the kick

The user requested a knee strike. `sample_paladin_knee.py` uses only the kick's
early chamber samples (0–3), adds a weighted 50-degree right-shin fold, and blends
from/to the current idle over sixteen frames. The knee leads the tucked boot at
contact: world forward is negative Y, knee Y is -0.46937 m and foot Y is
-0.39118 m. Contact remains on row 8 / action frame 9. Meshes, bindings, model
height and calibrated pixels per metre are unchanged. Ground correction targets
the idle's original boot height instead of lifting its endpoints to a new plane.
Final boot minimum Z is -0.006821007 to -0.006820712 m; planted-foot XY drift is
below 6e-8 m. Both endpoint poses return to the original idle placement.

The common renderer now defaults to southeast main light (3,-4,6), with northwest
sun-shadow rays derived from that light. Character rotation leaves the world
light fixed. This knee preview uses a full moving shadow, with distance gain 1:
no shrinking or held-idle substitution. Existing installed idle/walk assets have
not been relit by this code change.

`preview_paladin_attack.py` composes an uncropped review using a 256-pixel
overscan shadow render. The red rectangle marks the actual 1024-pixel cell.
All 128 body poses fit. Six northwest-facing shadow poses (one-based frames
6–11) cross the left boundary, by up to 56 NN8 pixels / 7 logical pixels.
The user explicitly asked to see clipping issues before they are fixed, so this
is a review candidate and has **not** replaced the installed WLNAT sheet.
Do not hide the overflow by shortening the shadow or rescaling the character.

Local work: `warrior-3d/paladin-knee/Paladin-knee-final-v2.glb`, `frames-final`,
`shadows-overscan`, `final-v2-measure.json` and `review/bounds.json`.
`review/knee-preview.gif` plays at the normal 50 ms per frame and shows S/W/NW;
`knee-contact-eight-directions.png` shows every facing at contact. Copies are
saved beside the edited model under `Unarmed Knee Review`. The previous kick
and installed game sheets remain intact. No engine or build-version change.

Reproduce by sampling the retargeted kick and idle without measurement, evaluating
that result with `measure_paladin_attack.py`, then resampling with the measured
ground/support input. Render with the existing attack reference (frames 0–15,
horizontal root motion preserved, sun (3,-4,6), shadow distance gain 1). For the
review, expand only the shadow render canvas from 1024 to 1536 and multiply the
camera's orthographic scale by 1.5, preserving pixels per metre; pass those
overscan shadows and normal body frames to `preview_paladin_attack.py`.

## Expanded renderer canvas and corrected tile anchor

The user requested a larger drawing area in our existing renderer and questioned
centering. Version 0.4.1-pre adds optional named-sheet canvas metadata, retaining
Classic simulation and original action selection. It does not replace the engine.
`assemble_paladin_canvas.py` authors 192 x 192 logical canvases at the existing
8x source density and calibrated scale 1.1334110707181562. The sidecar is
`D1R_SHEET_V1 8 96 160`; its fixed ground origin is (96,144), at the center of a
64 x 32 tile. The renderer aligns this anchor to the original Classic placement.

The previous per-direction body-bound fitting displaced the model's ground
origin by up to 3.22 logical pixels horizontally and 4.02 vertically. The new
assembler uses the camera-projected world origin (0,0,0), with a single transform
for every direction and frame. Extra canvas no longer changes apparent size or
position. The knee's full moving shadow fits without compression or clipping.

The same root anchor and southeast sunlight were applied to the existing short
walk and idle renders. The approved shortened motion, original row counts,
character geometry, darker palette, normal timing and source pixels per metre
are retained. AS still uses every second town-idle sample; AW and WL share the
approved eight-frame walk. All body and shadow cells fit in the expanded canvas.
Only light direction and registration changed in the idle/walk art pass.

Local outputs are `paladin-knee/output-expanded`,
`paladin-root-aligned/walk/output`, `paladin-root-aligned/idle/output` and
`paladin-root-aligned/idle/dungeon-output`. A local `anchor-audit.json` records
the old directional offsets. Preview crosses/diamonds show the fixed ground
origin and tile outline; those markers are never included in the game sheets.
See `docs/HD_SPRITE_SHEETS.md` for metadata and draw-position semantics.

The tested 0.4.1-pre executable and paired PNG/layout files are now installed.
The previous executable was backed up. Installation hashes were verified:

| Sheet | SHA256 |
| --- | --- |
| WLNAT | `8621F389C9A53377B1B9B4F6A5FA98F784FCDF7C39B0F8C56BAF94AF3649B6E9` |
| WLNWL / WLNAW | `F6F22D1DBC07864AD7811228A724589764387F8142B9B8868AEA0B3E81DBEEA7` |
| WLNST | `B725C299A7DF064B6A281D6257832550EC86B8982AADE0678E782E6C186C2607` |
| WLNAS | `9CB2ACB8FAECDCED614B69090197E4E0D6506F2D1496137EE61E21931595482F` |

Copies and correctly named previews are local under `Expanded Canvas 0.4.1`.
The decoder/compositor regression tests passed, including streaming the actual
expanded knee sheet. The 4,853-frame gameplay replay retained its reference-save
outcome. A separate full-game saved unarmed Warrior replay loaded the expanded
idle sheet and passed HD/Classic switching, menus/panels and zoom; normal/zoomed
GPU frames were reviewed. The knee sheet has render/geometry/compositor coverage;
its actual attack feel/hit contact still needs live gameplay verification.

`overlay_vanilla_paladin.py` produces local idle/walk/attack body-silhouette
comparisons: cyan is the original decoded CL2 body (palette-zero shadows
excluded), magenta is our current body, white is shared coverage, and green is
the tile ground origin. Original cells are placed using their canvas center and
bottom baseline; new art uses the actual camera-derived root registration and
approved art scale. Neither is independently resized or body-bound centered.
The animation comparisons use matching game row counts and timing. Vanilla AT is
a punch whereas the replacement is a knee, so pose differences are intentional.
Outputs are local under `paladin-knee/vanilla-overlay` and copied to the asset
archive's `Expanded Canvas 0.4.1/Vanilla Overlay` directory. No installed files
were changed for this comparison.

## Separate authored punch preview

The user asked whether we could make a punch. `create_paladin_punch.py` authors a
new straight right punch from the current idle, without replacing the installed
knee. It solves the upper-arm/forearm chains in glTF world coordinates, keeps a
left-hand guard, adds a small torso wind-up/follow-through, straightens the wrists
and curls the four finger chains into fists while preserving source thumb poses.
The finger mapping is specific to this Paladin rig, not a general humanoid rig.

The sixteen poses have exact idle endpoints and contact on the ninth game frame.
Only bone rotations change. Meshes, materials, skin bindings and node records
are retained; no Blender scene re-export is involved. The actual imported result
was measured: both feet remain stationary and minimum boot height stays exactly
-0.006820822 m across all sixteen poses. Model height, source density and the
fixed tile-ground anchor are unchanged. Full moving shadows use southeast sun.

Initial previews exposed a bent wrist and open-hand appearance; the reviewed
version (`Paladin-punch-v3.glb`) aligns the knuckle axis with the forearm and uses
the correct mirrored finger-curl direction. Body, guard, fists and contact pose
were visually inspected. The expanded-canvas assembler supports a clean preview
without the optional anchor guide. Local work is `paladin-punch`, and the local
asset copy is `Unarmed Punch Preview`. This is an offline animation candidate;
no executable, installed sheet or build version is changed by this preview.
All 128 body and full moving shadow cells passed expanded-canvas checks. The
preview GIF plays sixteen frames at 50 ms each. The compatible candidate atlas
and its layout are saved locally for possible later testing, not installed.

## Punch refinement after rigid-motion feedback

The user rejected the first punch as too rigid. The revised authoring pass adds
root/hip yaw, forward/lateral weight transfer, body dip, stronger delayed shoulder
rotation, an arcing accelerating hand path, left-hand counter-motion, forearm
pronation and a longer follow-through/recovery. This supersedes the earlier
rotation-only prototype: root translation now changes as part of the animation,
without scaling geometry or moving the game tile. Hip yaw ranges from -6.88 to
13.18 degrees; the combined shoulder turn reaches about 23 degrees. Body dip is
up to 3.78 cm. Both idle endpoints and ninth-frame contact remain fixed.

Both legs are solved against the original ankle positions, with their original
foot orientations. Reach is checked before solving; hips lower enough to avoid
overextending either planted leg. Imported-result measurements show foot drift
below 3e-7 m and boot minimum Z from -0.006820925 to -0.006820654 m. There is no
sliding, model-height scaling or altered attack/gameplay timing. All 128 body and
moving-shadow cells fit the expanded canvas and use the southeast sun rule.

Local work is `paladin-punch-fluid`; copies are in `Unarmed Punch Preview/Fluid
Pass`. `punch-before-after.gif` compares the old and revised west views at the
same display scale, anchor and normal playback speed. This remains an offline
preview candidate, with the knee still installed and no executable/version change.
