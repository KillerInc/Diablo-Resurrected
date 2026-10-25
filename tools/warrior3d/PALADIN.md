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

## Selected punch and restored original NN8 dimensions

The user selected the revised full-body punch, and clarified that the desired
size was the original NN8 size before adding shadow canvas. The assembler now
accepts explicit `canvas_logical` and `canvas_anchor` metadata. All five custom
unarmed sheets were rebuilt at their original dimensions and installed, with the
revised punch replacing the knee. The 0.4.1-pre executable is unchanged; optional
expanded-canvas support remains available for future assets.

Attack cells are 128 logical / 1024 source pixels, anchor (64,128). Idle/walk
cells are 96 logical / 768 source pixels, anchor (48,96). These agree with the
original Classic canvas-center and baseline placement. Model scale, shortened
walk, ninth-frame punch contact, corrected root alignment and southeast sunlight
are retained. Every body and full moving shadow fits without trimming or extra
shadow compression. PNG dimensions were compared directly with the user's
original NN8 files before installation, and installed hashes were verified.

| Sheet | Original/restored PNG size | SHA256 |
| --- | --- | --- |
| WLNAT | 8192 x 16384 | `30479C2A4480C55F8FC788F7E555B69A816FB5D88F0660B8D0C8C22DF4463B1A` |
| WLNWL / WLNAW | 6144 x 6144 | `84EC2D63A2FC5220850EF222BEBE6B2C6B9025732AB841A4DBFA4DF00E840438` |
| WLNST | 6144 x 15360 | `396DBCDBE0C01BDF43EE084A2DAC5B49B58E3FBD84412DADD0B1F34D4774F087` |
| WLNAS | 6144 x 7680 | `E3E924620B19BDC1B0578B0817D591D38DF09281974B9F1DBE3B95591C3286EF` |

Local work and the install manifest are under `paladin-vanilla-dimensions`;
asset copies and the punch preview are under `Vanilla NN8 Dimensions`. Prior
expanded sheets, knee and punch prototypes remain in their separate asset
directories. No proprietary art is included in Git.
The installed 0.4.1-pre executable completed the isolated 2,700-frame full-game
HD/Classic/zoom/UI replay with exit 0. Its log confirms the restored WLNST loads
at 1536 x 3840 retained pixels, twenty frames and 2x density. This replay has no
final reference-save comparison and does not exercise the new punch in combat.

## Native Paladin animation library and hit reaction

The user supplied `palm_all_anims.glb` in the edited candidate folder. It contains
330 clips, 816 source nodes and 193 animated bones; every animated bone matches
our edited Paladin. Maximum rest-matrix difference is 1.01291e-5. The local
catalog records each clip's maximum sample count/duration across all samplers,
not just the root sampler. Model geometry and skin/node records are retained.

`select_paladin_animation.py` extracts one exact named clip, packs only needed
accessors (including inverse-bind matrices), and preserves the source node/skin
hierarchy. The animation-only result is attached with `merge_paladin_walk.py`.
The imported 190 MB library stays private; a single reaction's animation data
compacts to about 249 KB without changing its samples. Local catalog and selected
models are under `paladin-native-animations`.

HT now uses native `palM_HTH_reac_flinch_B`, with original source samples
0,5,10,15,20,25 from its 26-sample / 0.8333-second motion. This fills vanilla's
six hit-recovery frames at its unchanged game timing (0.3 seconds normally).
The generic get-hit and front-flinch candidates were rejected because their
full projected shadows exceeded original cells. Back/left/right flinches passed
a geometric shadow audit; backward recoil was chosen for the default reaction.
All 48 rendered body and full moving shadow cells pass the final crop checks.
Source feet remain stationary; minimum boot Z is -0.00679803 m across selected
poses. No shadow shrinking, extra canvas or model scaling was used.

Installed WLNHT is 6144 x 4608 RGBA, with `D1R_SHEET_V1 8 48 96` layout and SHA256
`8FC222DC004105F9E70D68A0CE9601B3CC840EB5AA01689C7543CBE23BE1F36B`.
Installed punch hash was rechecked and is unchanged. Preview/source copies are
in `Native Paladin Hit Reaction`; the current NN8 install manifest includes HT.
The raw GIF uses normal six-frame timing. The paused GIF adds idle holds only
for review; installed gameplay timing is unchanged. This native HT has offline
render/geometry validation; taking hits in live gameplay still needs verification.

A procedural six-frame hit draft was prepared before this library arrived, but
was not installed. Its optional `hit` authoring profile is retained as a draft;
the default approved punch generator was checked to remain byte-identical after
adding that profile. The native clip supersedes this draft for the installed HT.
The generic canvas assembler accepts a preview contact-row override for short
actions. No executable/build version changed for these asset updates.

Inventory cautions for subsequent work: the library's `palM_hth_reac_death`
contains only two samples (0.0333 seconds), so do not assume it is a complete
fall/death motion. No explicitly HTH attack or block/parry-named clip was found
in the catalog; keep the user-approved authored punch until another is reviewed.
Prayer/scroll events and weapon-specific attacks are present and need individual
inspection before mapping them to further D1 actions.

## Native death collapse and original rectangular death cells

DT now uses `palM_HTH_event_faint` from the user's native library: a complete
46-sample / 1.5-second collapse ending on the ground. The named
`palM_hth_reac_death` was inspected and proved to be two identical standing
poses. Knockdown was also inspected; its end remains propped up rather than
fully resting. No missing fall was assumed or invented.

The raw faint ends off-center, with opaque armor as low as -0.1312 m. An uncropped
three-view preview showed the original-cell overflow before corrections.
`prepare_paladin_fall.py` evaluates the existing model and prepares render-only
offsets: floor contact matches the idle's -0.00682082 m minimum, and a smooth
fall-height-driven translation settles toward one fixed final footprint center.
The final center is computed once, not refitted separately per facing/frame.
A smooth two-logical-pixel upward image placement during settling leaves space
for the full soft shadow in the original rectangle. These identical placements
apply to body and shadow in all directions. Geometry, joint animation, pixels
per metre, light direction and shadow length remain unchanged.

Vanilla DT cells are rectangular: 128 x 96 logical / 1024 x 768 NN8 pixels.
`prepare_town_walk.py` now obtains row count from CL2 and keeps separate cell
width/height; `assemble_paladin_canvas.py` accepts rectangular canvas metadata
and letterboxes its previews without stretching. Default square output was
regression-checked: the installed HT atlas rebuilds byte-identically. Rendering
and shadow projection share per-pose placement metadata; it defaults to zero
for previous actions.

Source samples are `round(i*45/19)` for twenty rows, including the final pose.
The game retains vanilla's two ticks per death frame (normally 100 ms), so the
twenty-row action lasts two seconds and the existing game holds the last corpse
pose. Preview holds before/after the fall are review-only. All 160 body and full
moving northwest shadow cells fit, with a minimum 10 NN8-pixel shadow margin.
Model scale remains 1.1334110707181562; no canvas enlargement or shadow shrinking.

Installed WLNDT is 8192 x 15360 RGBA, with `D1R_SHEET_V1 8 64 96` layout and SHA256
`3B3DFB6AE33A617B0547D47CDFAB3A7904254C843464B551A87C60EAE988DCA9`.
AT and HT hashes were rechecked unchanged. Local work is `paladin-native-death`;
copies are in `Native Paladin Death`. `Native-Source-Faint.glb` is explicitly the
unaltered native source; grounding/settling is applied by the accompanying JSON
during rendering, not baked into that GLB. The current NN8 install manifest now
includes DT. No executable/version change. Live death/corpse behavior still needs
gameplay verification; validation here covers source poses, render placement,
frame/dimension compatibility, shadow bounds and visual review.

## Foot-anchored directional death refinement

This supersedes the corpse-centering and two-pixel upward settling described
above. The same native faint clip now falls into the space available in each
original death cell, with no horizontal actor translation or image shift.
Twenty frames, 128 x 96 logical cells, original anchor, art scale and southeast
sun remain unchanged. Other installed actions and the executable are unchanged.

`prepare_redirected_paladin_fall.py` accepts the merged native model, original
death reference, output reference and existing scale calibration. It checks
sixteen possible fall-axis adjustments against all twenty poses and eight
views, then selects the smallest adjustment with over 18 NN8 pixels of geometric
body/shadow clearance and less than 5 mm of leg-target error. Selected angles
for S/SW/W/NW/N/NE/E/SE are 0/+22.5/+67.5/-22.5/0/0/0/0 degrees.

`redirect_paladin_fall.py` redirects pelvis travel and the axis of its rotation
relative to the starting pose. The correction acts through `attach`, the shared
parent of torso and pelvis, so the torso seam stays intact. Both legs use
two-bone IK, retaining native individual ankle motion while removing the pair's
common horizontal drift. Their midpoint stays at the initial stance location;
feet can fold and release during the fall. Native relative upper-body animation
is retained. Grounding adds vertical offsets only, independently per pose/view.

Body and shadow renderers share this pose correction. Native samples are cached
before temporarily disabling action evaluation: otherwise Blender's render
update overwrites manually corrected bones. Every body render checks that its
pelvis, head and ankle matrices survive rendering unchanged. The saved scene
restores the original action so the shadow pass can reproduce native samples.
Optional 512-pixel raw shadow overscan is now supported directly by the shadow
renderer; the output sheet itself is never enlarged.

Actual-rig validation over 160 poses found maximum initial matrix error
2.58e-6, ankle-midpoint XY error 5.25e-7 m, and ankle-target error 1.50e-6 m.
These are numerical tolerances; the initial pose/facing and stance midpoint are
preserved. Local work and provenance are under `paladin-native-death/redirected`.
No proprietary input, pose data, preview or atlas is committed to GitHub.

Final rendered-alpha validation passes all 160 body and 160 shadow cells, with
minimum margins of 27 and 16 NN8 pixels respectively, including shadow blur.
The eight-facing motion contact sheet was reviewed before installation. Revised
WLNDT SHA256 is
`AEAA9352157B5917828E769EEBE5A38B0E5E46F5F4A3B78D00B9D0250F56784D`.
Installed PNG/layout and all six other installed action hashes were verified.
The local asset archive is `Native Paladin Death/Foot Anchored`; its eight-view
GIF holds the first and final poses for review only. Live in-game death/corpse
behavior remains unverified; this pass validates the animation and rendered
atlas, not a new engine build.

## Preserve native legs during redirected death

The separate ankle IK from the preceding refinement caused unnatural inward
knee bends and has been removed. The current method changes only the shared
`attach` motion parent, including the translation needed to keep the stance
midpoint at its original XY position. It preserves the native relative poses
of both hips, knees, ankles and feet throughout the fall. The feet can pivot
and release together; individual ankle trajectories are no longer forced.
The fall axis is still redirected to fit each original cell, and grounding
still uses vertical offsets. Neither sheet dimensions nor model scale changes.

The renderer helper asserts that all eight thigh/shin/ankle/foot local matrices
stay native. Independent validation of all 160 poses compared every local bone
matrix except the intentionally changed `attach`: maximum difference 4.77e-7.
Maximum starting-pose matrix error was 6.56e-7, and stance midpoint XY error was
2.81e-7 m. The source animation's leg articulation is therefore preserved within
numerical tolerance, rather than merely meeting a foot-position constraint.

The updated smallest fitting fall-axis adjustments in S/SW/W/NW/N/NE/E/SE order
are +45/+90/+90/-112.5/-67.5/0/0/0 degrees. These redirect the fall motion, not the
initial facing. Bounds selection requires 18 NN8 pixels of clearance and less
than 0.01 mm of stance-midpoint error. Local work is
`paladin-native-death/natural-legs`. Previous IK atlases remain local history.

All 160 final body and shadow cells pass rendered-alpha checks with minimum
39/25 NN8-pixel margins respectively. The eight-view motion review was inspected.
The installed WLNDT SHA256 is
`CF531897CB98643D54A79D217D72003BA25A4658BA42AA6D44033EEBCEE611AB`.
PNG/layout and all six other action hashes were verified after installation.
The current local archive is `Native Paladin Death/Natural Legs`; the eight-view
GIF holds its first/final frames for review. Original atlas dimensions, 20-frame
game timing, scale, southeast light and executable remain unchanged. Live
gameplay review is still required for the final appearance in motion.

## North and northwest landing correction

The pelvis-based steering left the N/NW endpoint too upright despite preserving
native joint poses and fitting the cells. Those two views now use `body_axis`
steering: rotate the current head-to-stance axis around its initial upright axis,
then apply the minimum rigid turn carrying the current axis to that target.
This preserves the starting pose, native joint articulation and stance midpoint
while keeping the final body axis low. Other facings retain the previous method.

`prepare_paladin_death_facings.py` accepts model/current-reference/output/scale
calibration, refines only directions 3/4 and preserves all other facing metadata.
Candidates must fit all twenty body/shadow poses, preserve the stance midpoint,
and have final opaque height below 0.60 m. Selected body-axis adjustments are
NW -90 and N -45 degrees. Body/shadow renderers honor optional `render_directions`
to regenerate only these columns while reusing the other six raw renders.
Local work is `paladin-native-death/north-refinement`. Sheet dimensions, scale,
timing, native leg poses, southeast light and the executable are unchanged.

All 160 final body/shadow cells pass rendered-alpha bounds checks; minimum
body/shadow margins are 39/35 NN8 pixels. The six untouched atlas columns were
compared by pixel hashes and are identical. Native local-joint matrix error
remains below 4.77e-7 and stance midpoint XY error below 2.81e-7 m over all views.
The N/NW before/after motion contact sheet was reviewed before installation.
Current WLNDT SHA256 is
`ED12575F0907C5C9A2B56BBBC0A499A463B4E192AD69D7C1F56D0FA9AFC6588E`.
All seven installed action hashes were verified. Local archive:
`Native Paladin Death/North Northwest Refined`. Live gameplay review remains
outstanding; no executable was changed.

## Unarmed fire casting

Warrior unarmed has no WLNBL sheet in the original assets. In `items.cpp`, only
Monk equipment exceptions or a shield enable blocking; `player.cpp` skips BL
loading without that flag. The next applicable unarmed action is fire casting,
FM. `assets/txtdata/classes/warrior/animations.tsv` defines twenty casting frames
and release on frame 14; `DoSpell` uses that action frame. No gameplay timing or
blocking rules are changed.

Four native gestures were visually compared: the two Harbinger unleash clips,
use-scroll, and `palM_HTH_event_use_resurrect`. The resurrection gesture provides
an empty open-hand extension, without the unleash roar or scroll-reading pose.
The exact clip was extracted with the existing selector and merged onto the
current edited model: 193 animated bones match, with maximum rest difference
1.013e-5. The mesh, skin bindings, nodes and texture data remain unchanged.

`create_paladin_cast.py` takes that merged native clip, current animated idle,
output GLB and optional gesture strength. It samples the native gesture so frame
26 falls on output frame 14, blends into/out of the exact first idle pose, and
fixes horizontal stance midpoint through root translation. It does not solve
individual legs. The selected strength is 0.43, with upper-arm weight multiplied
by 0.65; anatomical elbow flex adds up to 55/20 degrees left/right and is capped
at 125 degrees. A 25-degree casting-wrist extension presents the palm forward.
The envelope removes all adjustments at both endpoints. These are pose edits,
not changes to model size or shadow projection.

The initial full gesture's west/northwest shadow overrun was shown before
refinement. The casting arm is now kept closer to the body. Original NN8 FM is
6144 x 15360, twenty 768-square cells per column; the sidecar remains
`D1R_SHEET_V1 8 48 96`. The installed art scale and full southeast-to-northwest
shadow projection remain unchanged. This initial replacement omitted casting
flames baked into the vanilla FM sprite; the game supplies the separate spell
projectile. Local work is `paladin-casting`, with
the selected output under `fire-palm`.

All 160 final body/shadow cells pass rendered-alpha clipping checks, including
blur; minimum body/shadow margins are 53/5 NN8 pixels. Starting/ending body alpha
is identical in all eight views. RGB differences are limited to renderer rounding
(at most 2/255 over at most fifteen pixels in each 768-square cell); authored idle
endpoint transforms are exact. Release mapping and all source/buffer preservation
assertions pass. The rendered motion contact sheet was reviewed.

Installed WLNFM SHA256:
`FD91AF0CBDE40DE5F614421CCEB78C986B632865132BA556DA53B9654A6FBE91`.
The previous installed FM PNG (SHA256
`40364A4AE2E9694DC31F2F9357A1344E049912087AA0B9DC849F1A5D2283D791`, no
layout sidecar) is preserved under `Unarmed Fire Casting/Previous Installed`.
The selected GLB, atlas, previews and private provenance remain in `Unarmed Fire
Casting`. The current install manifest now has eight custom actions; all eight
installed hashes were verified, with the other seven unchanged. The eight-view
GIF adds review-only endpoint holds; gameplay still uses twenty 50 ms frames.
No executable/build change. Live projectile/cast appearance remains to be checked
in game. Lightning and other-magic sheets are still the previous installed art.

A synchronized comparison with the original NN8 WLNFM confirmed that vanilla
contains prominent casting flames within the sheet itself, including frame 14.
That initial character-and-shadow replacement lacked that layer. The prior claim
that the game would supply the complete casting effect was incorrect; only the
separate projectile is handled independently. This motivated the fire remake
described below. Comparison GIFs use matching cell
scale/anchor, all twenty frames at 50 ms, and S/W/NW views. They remain local in
`Unarmed Fire Casting/Comparison`; no artwork was committed. The installed sheet
was not changed during this comparison.

## Fire remake and a closer casting motion

The vanilla sequence gathers inward, expands a fire enclosure around the caster,
then opens the arms while the upper fire recedes into lower arcs/ground flare.
Five additional male-class motions were extracted and retargeted for comparison:
Sorcerer flame-shield, frost-nova, firewall, fireball, and Necromancer blood-surge.
The closest tested gather/open motion is `sorM_wndoh_attk_firewall`, transferred
with `retarget_paladin_kick.py` to the same edited Paladin mesh. Fifty-one named
bones/ancestor helpers were transferred; class-specific muscle tracks were not
copied. Paladin geometry, bindings, rest nodes and texture buffers are preserved.

The new ritual profile in `create_paladin_cast.py` samples source frames
`0,0,0,0,2,4,6,8,10,12,14,16,18,20,22,24,27,30,33,35` at strength 0.85. Source
pose 20 maps to output frame 14. It retains current idle endpoints, anchors the
stance midpoint, keeps feet oriented for a standing cast, and uses compact arm
targets/downward elbow poles with a maximum 130-degree elbow bend. This adapts
the native reach to the original cell/shadow limits while retaining the torso
and gather/open rhythm. Floor-contact offsets are applied equally to body and
shadow; no model or shadow scaling changes.

`paladin_fire_effect.py` builds deterministic 3D flame ribbons with turbulent
shading, hot cores, ground ring, central flare and embers. The broad enclosure
faces the fixed sprite camera in every direction, as it reads in the reference;
the actual geometry still passes in front of/behind the rotated character.
The upper arc fades into the lower flare before recovery. Its seeded twenty-row
clock starts/ends with fire off and remains synchronized to the vanilla release.
An orange point light adds brief fire illumination without casting new shadows.
The standard southeast character-shadow projection still uses only body geometry.

The body renderer writes an emission-only grayscale mask alongside each render
using Blender 5.1's compositor group/file-output API. The assembler grades the
character with the existing dark treatment, preserving luminous fire colors
through that mask. Idle masks are zero. The shadow renderer disables the fire
compositor so it cannot overwrite masks. `render_rows` permits limited prototype
renders; full atlas output uses all twenty rows and all eight directions.

The shared assembler rebuilt the existing HT atlas byte-for-byte unchanged
(`8FC222DC004105F9E70D68A0CE9601B3CC840EB5AA01689C7543CBE23BE1F36B`). The previous
resurrection-based cast profile also regenerates an identical GLB (SHA256
`117EF54EB915E98A0AD80CAEECB7E033D1A3F8FA894051B228CA2D48BDF29205`).
All models, renders, masks, comparisons and candidate data remain local under
`paladin-fire-remake`; the selected body is `ritual-final/Paladin-fire-cast.glb`.
The effect is a procedural remake, not a pixel-identical reconstruction of the
original flames. No proprietary images or animation data are committed.

`prepare_paladin_fire_reference.py` reproduces the twenty vertical floor-contact
offsets from the body mesh and original FM reference, and writes original-size
layout, fire seed, source frames and preview settings. The renderer carries
those settings into its output metadata, so the command-line pipeline does not
depend on hand-editing the reference or render JSON. Regenerated grounding and
pose settings were compared to the production reference and match exactly.
After the AgX render, emission-masked fire colors receive a warm gold tint;
the existing body grading remains unchanged outside the fire mask.

Final output passes 160 combined body/fire and 160 full-shadow cell bounds checks,
with minimum margins 18/9 NN8 pixels. All 160 emission masks exist, idle masks are
zero, and first/last silhouettes match in all directions. The new cast's initial
silhouette is also pixel-identical to the previous cast in every facing: model
size and anchor are preserved. Synchronized vanilla/previous/new and all-facing
contact sheets were visually reviewed before installation. The brightened fire
pass reused the unchanged character-shadow renders after verifying identical
pose, camera, ground-origin, sun and shadow settings.

Previous firewall-remake FM SHA256 (superseded by the Gizmo bubble below):
`E7511559FE0FF181AD3AAF8C40EF9C85DD7A26DD6CA2AC1DB27D61827E6EAABC`.
Current output is `ritual-final/output-strong`, body frames/masks are
`ritual-final/frames-strong`, and the local asset archive is
`Unarmed Fire Casting/Fire Remake`. The previous FD91... hand cast PNG/layout are
preserved in that archive's `Previous Cast` folder. All eight installed action
hashes were verified; the other seven are unchanged. The archived GLB is named
`Paladin-cast-body.glb`: it contains the body animation/textures, while the new
flames are generated during rendering and baked into the installed PNG.
Review GIFs pause before/after the synchronized one-second sequence; gameplay
still uses twenty 50 ms frames with release at frame 14. No executable/version
change. Live spell/projectile appearance remains to be reviewed in game.

### Native Gizmo Operate and a full fire bubble

The user identified the interaction as **Gizmo Operate**. The local Paladin
`pal_Interact.ans.json` maps Power `Gizmo_Operate_Generic` to
`palM_hth_event_use_generic`; it is not named "tinker" in the exported animation
list. The same Power has separate class-specific clips. This revision uses the
Paladin clip directly on the matching 193-bone rig, preserving its native hand,
arm and corrective-bone motion rather than adapting the Sorcerer firewall pose.

`create_paladin_cast.py` samples native frames 32–62 over twenty output frames.
The middle gesture has full native weight, with smooth transitions to the exact
existing idle pose at both ends. No arm IK, elbow flex, wrist extension or
shoulder clamps are applied to this profile. Root stance drift is corrected and
vertical-only mesh-derived floor offsets keep ground contact; geometry, textures,
bind data, body height and fixed registration remain unchanged. Gameplay still
controls the twenty-frame cast and release at frame 14.

`paladin_fire_bubble.py` adds a seeded, animated ellipsoidal flame shell enclosing
the character, with transparent front veins, a brighter rim and surface flames.
`paladin_fire_effect.py` selects it with `fire_effect.style = "bubble"`; the prior
effect remains available without that setting. The bubble is generated in 3D
and baked into the FM sheet. It casts no character shadow. Fresh anatomical
shadows were rendered from the unchanged southeast sun. Body grading stays dark
outside the separate emission mask. To reproduce the reference settings, pass
the optional `bubble` argument to `prepare_paladin_fire_reference.py`.

Production files remain private under `paladin-fire-bubble/gizmo-final`:
`frames`, `body-only-frames`, `shadows`, and `output`. The installed sheet remains
6144×15360 with twenty 768×768 cells per direction and sidecar
`D1R_SHEET_V1 8 48 96`. Scale is 1.1334110707181562 and the fixed foot origin is
(384,640). All 160 body/fire and 160 blurred-shadow cells pass strict bounds
checks, with minimum margins 27 and 5 NN8 pixels respectively. All 160 emission
masks exist; first/last masks are empty and silhouettes match in every direction.
The all-facing contact, previous/new comparison and body-only south/west preview
were visually reviewed. No clipping was corrected by scaling the model, changing
the canvas or shortening the shadow.

Installed FM SHA256:
`86BD84E7AD5EA161F255C943DBD74B8A91452F1723515BEDC3080224CA1B83FA`.
The local archive is `Unarmed Fire Casting/Gizmo Fire Bubble`, with the previous
E751... sheet/layout under `Previous Cast`. `Paladin-gizmo-body.glb` contains
the body animation; the procedural bubble is baked during rendering. The current
NN8 mirror and install manifest were updated, and all eight installed hashes
were checked before and after: only FM changed. No game executable or version
change. In-game spell/projectile appearance still needs a gameplay review.
Only scripts and these notes are committed; no models, animation tracks,
textures, sheets, masks, extracted metadata or preview artwork enter Git.
