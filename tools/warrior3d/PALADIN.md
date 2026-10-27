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

### Lightning casting (LM)

LM continues the approved native Paladin Gizmo Operate motion without changing
the body animation, armor, geometry, scale or anchor. The original NN8 LM PNG is
6144×16128, and all eight original CL2 direction headers contain 21 frames.
Warrior `animations.tsv` still specifies twenty gameplay casting frames and
release at frame 14. The original-size output therefore retains 21 stored rows:
rows 0–19 use the approved twenty poses and the spare row 20 repeats final idle.
The hand motion is not stretched across an extra gameplay frame.

`prepare_paladin_lightning_reference.py` verifies the original LM direction
counts and derives the LM reference from the approved grounded FM reference.
`paladin_lightning_effect.py` creates deterministic blue-white, forked 3D arcs
from the hands around the lower body, reflecting the original LM's baked
electrical casting effect. It uses separate emission masks, a small shadowless
blue light and the existing renderer. Electrical grading preserves cool colors;
the fire grading path remains unchanged. The arcs fade completely at idle and
do not cast shadows. This is caster artwork only: engine spell/projectile
selection and timing remain unchanged.

Private production data is under `paladin-lightning`: `reference.json`, `frames`,
`shadows` and `output`. Fresh anatomical shadow renders use the southeast sun,
full original shadow length and the same fixed registration. The sheet sidecar
is `D1R_SHEET_V1 8 48 96`, with 768×768 cells and fixed foot origin (384,640).
Review GIFs compare vanilla NN8 and the new caster at the same cell size in
south/west views, and show all eight new facings. The GIF plays the twenty
gameplay frames at 50 ms each; the PNG retains all 21 original stored rows.

All 168 combined body/effect cells and 168 blurred-shadow cells pass strict
bounds checks. Minimum margins are 58 and 5 NN8 pixels respectively. All 168
emission masks exist; masks are empty in rows 0, 19 and 20 for every facing, and
those idle silhouettes match. The approved FM body GLB was reused without edits.
The original FM effect remains installed and its hash is unchanged.

Installed LM SHA256:
`60A27507B3149C6774665381CF0C459D5DDC02D95E8F15C033D410EB64A5BDFE`.
The asset archive is `Paladin Candidate 1 Edited/Unarmed Lightning Casting`,
with the previous installed vanilla sheet in `Previous Vanilla Sheet`. The
current NN8 mirror and install manifest now contain nine custom actions. All
eight previously approved sheet hashes were verified before and after LM
installation. Only LM changed. Scripts and documentation are committed; all
proprietary source data, models, sheets, masks and comparisons stay local.
The executable remains 0.4.1-pre; this asset-only change requires no rebuild.
Live lightning spell/projectile appearance remains to be checked in game.

### Other-magic casting (QM)

The vanilla NN8 QM reference is 6144×15360 and each of its eight original CL2
directions has twenty frames. Its baked casting effect consists of blue motes
spiralling upward around the character. This revision retains the approved
twenty-pose native Paladin Gizmo Operate body animation and replaces only the
casting effect. Model geometry, armor, scale, registration and floor offsets
remain identical to the approved FM cast; gameplay release stays at frame 14.

`prepare_paladin_magic_reference.py` verifies the original QM frame counts and
derives a QM reference from the approved grounded FM reference.
`paladin_magic_effect.py` creates 640 seeded blue motes in four rising spiral
streams. The particles are placed in 3D, so the body occludes the rear streams.
The effect uses a separate emission mask and a small shadowless blue light.
The existing dark body grade is retained outside emission, and the cool grading
path used by LM also handles QM. Fire and lightning effect selection are unchanged.
The spiral grows upward, then fades to empty masks at both idle endpoints;
unlike vanilla's lingering final particles, this avoids a jump back to idle.
No spell missiles or gameplay behavior are changed.

Private files remain under `paladin-magic`: `reference.json`, `prototype`,
`frames`, `shadows` and `output`. New anatomical shadow renders retain the
southeast sun and full shadow length. The final sheet uses twenty 768×768 cells
per facing, sidecar `D1R_SHEET_V1 8 48 96`, scale 1.1334110707181562 and foot
origin (384,640). Synchronized south/west GIFs compare vanilla NN8 and the new
effect at the same cell size; a second preview shows all eight new facings.

All 160 body/effect cells and 160 blurred-shadow cells pass strict bounds
checks, with minimum margins of 7 and 5 NN8 pixels. All 160 emission masks
exist, idle endpoint masks are empty, and endpoint silhouettes match in all
eight directions. Initial raw body silhouettes are also pixel-identical to
the approved FM cast in every facing. No canvas expansion, scale change or
shadow shortening was used to fit the effect.

Installed QM SHA256:
`29115ECCB7D17C6C41A3D52A594A6A9933D714261AC60631BEE7D84F23D31AAC`.
The local archive is `Paladin Candidate 1 Edited/Unarmed Magic Casting`, with
the previous installed vanilla sheet in `Previous Vanilla Sheet`. The current
NN8 mirror and install manifest now contain ten custom actions. All nine
previous custom sheet hashes, including FM and LM, were checked before and
after installation and remain unchanged. Only QM was replaced. Source and
notes are committed; proprietary models, textures, animation data, references,
sheets, masks and preview art remain local. The executable hash still matches
`52B3E407DE77ABC1E0CA5B4D567736388BE4046B31BA036269F615D0941AA28B`:
version 0.4.1-pre, with no rebuild for this asset-only change. In-game spell
selection, projectile appearance and visual transitions still need gameplay
review.

#### Larger QM particles

At the user's request, the installed QM now doubles each particle's diameter
with `fire_effect.particle_scale = 2`. Particle count, seed, paths, timing,
colour, lighting and body animation are unchanged. The default scale remains 1
to reproduce the earlier version; `prepare_paladin_magic_reference.py` accepts
an optional final particle-scale argument. Only mote geometry changes.

The larger version passes all 160 body/effect and shadow bounds checks, with
minimum margins of 5 NN8 pixels for both. All emission masks exist, idle masks
are empty, and idle silhouettes match. Existing anatomical shadows were reused
after checking identical pose, camera, registration and shadow metadata.
The before/after south/west preview was reviewed before installation. All nine
other custom action hashes are unchanged; only QM was replaced.

Current QM SHA256:
`114A81A5C10832E67E04A393D417317F6615A12FBBF13225DC9A4F07CE8FB873`.
Private output is `paladin-magic/larger/output`; the archive is
`Unarmed Magic Casting/Larger Particles`, with the previous sheet/layout under
`Previous Small Particles`. The current NN8 mirror and manifest were updated.
No executable/version change; gameplay appearance still needs in-game review.

#### QM Option 2: orbiting ground emitter

The user retained the doubled-particle spiral as **Option 1** and requested an
alternative emitter orbiting the character at ground level, with its emitted
particles circling and rising. `paladin_magic_emitter.py` implements this as
birth-time-driven motion: one compact source follows a radius-0.53 ground orbit,
each mote retains its emission angle, then advances in angle and height with
age. Motes do not wrap or teleport from the top back to the ground. The source
has a short ground trail; particles disperse slightly as they rise. It uses
320 seeded birth events, the same doubled particle sizes, blue material and
shadowless illumination, and fades out at the existing idle endpoint.

Select this profile with `fire_effect.motion = "ground_emitter"`; omitted motion
or `"spiral"` retains Option 1. `prepare_paladin_magic_reference.py` accepts an
optional motion argument after particle scale (`2 ground_emitter`). Body poses,
floor offsets, scale, canvas, timing and registration remain unchanged.
Anatomical shadows were reused after comparing all relevant render metadata.
Particle angular and vertical progression were verified across angle wrapping.

All 160 body/effect cells and 160 shadow cells pass strict bounds checks, with
minimum margins 40 and 5 NN8 pixels. All 160 emission masks exist, endpoint
masks are empty, and idle silhouettes match. The south/west comparison includes
**vanilla NN8, Option 1 and Option 2** at the same cell size and twenty 50 ms
frames. That contact sheet and the eight-facing review were checked visually.

Option 1's exact PNG/layout are preserved under
`Unarmed Magic Casting/Option 1 Larger Particles`, SHA256
`114A81A5C10832E67E04A393D417317F6615A12FBBF13225DC9A4F07CE8FB873`.
Option 2 is installed for testing and archived under
`Unarmed Magic Casting/Option 2 Ground Emitter`, SHA256
`1D484CB8638CDB523F32E250D6909AC052457D6DF58734E906CC6DCA1784B245`.
The current mirror and install manifest record both options and select Option 2.
All nine other custom sheet hashes remain unchanged. Private production files
are under `paladin-magic/option2`; no artwork or extracted data enters Git.
No executable/version change. In-game visual transitions still need review.

#### Option 2 refinement: faster, denser and dispersing

The user requested faster spin, more particles and increasing space between
particles as they rise, explicitly rejecting age-based fading. The selected
reference now sets `spin_speed = 1.5`, `emission_density = 2` and
`disperse = true`. Both source orbit and particle angular travel are 50% faster.
Emission uses all 640 seeded birth events instead of 320. Particle size,
material, body animation and lighting are unchanged. Quadratic age-driven radial
and angular spread, plus modest vertical variation, separate older motes.
There is no age-based dimming in this profile: emitted motes retain their
brightness until their lifetime ends. The existing whole-cast idle transition
still turns the effect off at the end of the action. Default settings reproduce
the previous Option 2; Option 1 remains independent.

Checks confirm doubled event count, increasing radial spread and equal particle
brightness at early/late ages. All 160 body/effect and 160 shadow bounds checks
pass, with minimum margins 17 and 5 NN8 pixels. All emission masks exist and idle
masks/silhouettes pass. The unchanged anatomical shadows were reused after
matching pose, camera and registration metadata. The reviewed previews include
previous/new Option 2 and vanilla/Option 1/new Option 2, plus all eight facings.

Current QM SHA256:
`1C8687D47F76F23FCD3E151528DC9DC77F045219C92F92FEEDB05EC193E4435F`.
Private data is under `paladin-magic/option2-fast`, and the archive is
`Unarmed Magic Casting/Option 2 Faster Denser`, including `Previous Option 2`.
The Option 1 archive hash and all nine other installed custom action hashes
remain unchanged. The current mirror and manifest select the refined Option 2
and retain both older options. No executable/version change. Live gameplay
still needs visual review. All art and extracted data stay local.

#### Option 2 second speed/density increase

At the user's request, emission is doubled again to 1,280 birth events and
`spin_speed` increases from 1.5 to 2.25 (another 50%). `particle_count` is now a
bounded optional setting, defaulting to 640 for reproducibility. The existing
640 seeded events remain the exact prefix of the larger seed pool. A midcast
sample increases from 416 to 831 live particles, excluding the ground source
trail. Particle size, outward age-driven dispersion and brightness are
unchanged; no age fading was added. Source orbit and particle travel both use
the new speed. Body poses and twenty-frame gameplay casting timing remain fixed.

Private production files are under `paladin-magic/option2-faster`. The comparison
includes vanilla, preserved Option 1 and the latest Option 2, as well as a
previous/new Option 2 preview. Existing anatomical shadows are reused only after
matching camera, poses, offsets, scale, ground origin and shadow metadata.

The new output passes all 160 body/effect and 160 shadow cell bounds checks,
with minimum margins 14 and 5 NN8 pixels. All 160 emission masks exist and idle
endpoint masks/silhouettes pass. Reviewed the eight-facing contact and the
previous/new and vanilla/Option 1/Option 2 comparisons before installation.
Current QM SHA256:
`B2FE99153435F8B3B7B933B4ECC1405A62536740833BB6D9155F59144FCFD62D`.
The local archive is `Unarmed Magic Casting/Option 2 Faster Denser v2`, with the
previous sheet/layout under `Previous Option 2`. The mirror and manifest select
this revision; Option 1 and all nine other custom sheets retain their hashes.
No executable/version change. Live gameplay still needs visual review.

#### Option 2: stronger spacing that increases with age

The user requested more spacing that grows over time. The new reference sets
`spread_strength = 3` (default 1 reproduces the previous version). Angular
dispersion is tripled, and the radial distribution broadens progressively with
particle age squared. Young particles remain concentrated at the ground source;
older particles fan into a wider, looser cloud. The modest radial centre shift
keeps this within the original canvas without changing the body or its anchor.
Vertical trajectories, 1,280 birth events, spin speed 2.25, particle size,
colour and brightness are unchanged. No age fading was added. A trajectory
check confirms much greater separation late in life with identical size and
brightness. Projected particle positions were checked before rendering.

Private output is under `paladin-magic/option2-spacing`. Previous/new Option 2,
vanilla/Option 1/latest Option 2 and all-eight-facing previews are retained.

All 160 body/effect and 160 shadow cell bounds checks pass, with minimum margins
11 and 5 NN8 pixels. All 160 emission masks exist and idle endpoints match.
Reused unchanged anatomical shadows after comparing pose/camera metadata.
The reviewed wider-spacing sheet is installed with SHA256
`F497B71F89A0613CFE9ED7AAE6A5037D94A0942B545F765BE12EBD385EE52368`.
The local archive is `Unarmed Magic Casting/Option 2 Wider Spacing`, including
`Previous Option 2`. The current mirror and manifest select it; preserved
Option 1 and all nine other custom action hashes are unchanged. No executable
or version change. Gameplay appearance still needs in-game review.

#### Option 2: second emitter

The user requested a second copy of the emitter. The reference now sets
`emitter_count = 2`: the second source and its full particle stream are rotated
180 degrees around the character's vertical axis. Both sources orbit in the
same direction on opposite sides. Each retains 1,280 birth events, spin speed
2.25, doubled particle size and spread strength 3. Total birth events are 2,560.
The copy preserves each mote's age, height, brightness and outward spacing;
no age fading, extra body lighting, geometry or gameplay changes are introduced.
Default emitter count 1 reproduces the previous version.

Projected positions of both sources were checked against the original canvas
before rendering. Private data is under `paladin-magic/option2-dual`. Previews
include previous single/new dual, vanilla/Option 1/latest Option 2 and all eight
facings. Body poses, camera, anchor and shadows remain the approved settings.

All 160 body/effect and 160 shadow bounds checks pass, with minimum margins
11 and 5 NN8 pixels. All emission masks exist; idle masks are empty and idle
silhouettes match in every direction. Reviewed raw release-frame appearance
and the all-facing contact before installation. Current QM SHA256:
`CB52CA9524AB2B0A463CF0A71B7269D62696355B41CD4DF6B21C4027E13B29D0`.
The archive is `Unarmed Magic Casting/Option 2 Dual Emitters`, including the
previous single-emitter sheet/layout under `Previous Option 2`. The current
mirror and manifest select dual emitters; Option 1 and all nine other custom
action hashes remain unchanged. No executable/version change. In-game visuals
still need gameplay review. Only source and notes enter Git; all art stays local.

#### Dual emitters: slower motion and wider age-driven spacing

The user requested slower motion and more space between particles over time.
Spin speed is reduced from 2.25 to 1.5, one third slower for both ground sources
and particle angular travel. Spread strength increases from 3 to 4: angular
dispersion and radial variation grow more strongly with age squared. Newly
emitted particles stay close to their source; older particles spread farther
apart. Particle size, seed, 1,280 births per emitter, rising trajectory and
brightness remain unchanged. No age fading is added.

`qm_dual_emitter_profile.json` records the current procedural settings without
artwork. Copy that object into a grounded reference's `fire_effect` setting to
reproduce this variant; model and camera references remain private. Production
files are under `paladin-magic/option2-dual-slower`. Previews compare previous
and current dual emitters, and vanilla/Option 1/current Option 2.

All 160 body/effect and 160 shadow bounds checks pass, with minimum margins
4 and 5 NN8 pixels. All emission masks exist; idle endpoint masks are empty and
silhouettes match. The saved procedural profile matches the production render
metadata exactly. Anatomical shadows are reused after pose/camera comparison.
The reviewed slower/wider sheet is installed with SHA256
`9B07727EE5DABB864AAB4F31CFBDF79EC028526DE941EEE621D8F109B3596C2C`.
The archive is `Unarmed Magic Casting/Option 2 Slower Wider`, with the prior
dual sheet/layout under `Previous Option 2`. The current mirror and manifest
select this revision. Option 1 and all nine other custom action hashes remain
unchanged. No executable/version change; live gameplay still needs review.

#### Dual emitters: wider ground orbit

The user requested greater emitter distance from the character. Ground radius
increases from 0.53 to 0.68, about 28%. `emitter_radius` is optional and defaults
to 0.53 to reproduce earlier variants. Both opposite sources and their ground
trails use the wider orbit. New particles start at this radius; the added radial
offset decreases with `(1-age)^2` as they enter the existing rising cloud.
This changes the ground-source distance without lifting or expanding the upper
cloud beyond the original sheet. Age-driven spacing, vertical motion, particle
count, size, brightness and spin speed remain unchanged.

`qm_dual_emitter_profile.json` records the selected radius. Projected geometry
was checked before rendering. Private production files are under
`paladin-magic/option2-ground-radius`; previews compare previous/new ground
orbits and vanilla/Option 1/latest Option 2.

All 160 body/effect and 160 shadow cell bounds checks pass, with minimum margins
4 and 5 NN8 pixels. All emission masks exist; idle masks are empty and endpoint
silhouettes match. The saved procedural profile matches production metadata.
Reviewed the early rising trail and all-facing contact before installation.
Current QM SHA256:
`6EF285E90AA21292CCBEAE1D53AF94A5A0D20CCF2273F58FE795E5FA008CB97B`.
The archive is `Unarmed Magic Casting/Option 2 Wider Ground Orbit`, including
the previous sheet/layout under `Previous Option 2`. The mirror and manifest
select the wider orbit. Option 1 and all nine other custom action hashes remain
unchanged. No executable/version change; live gameplay still needs review.

### QM final approval and next equipment set

The user selected the latest Option 2 wider-ground-orbit QM as final. Its
approved SHA256 remains
`6EF285E90AA21292CCBEAE1D53AF94A5A0D20CCF2273F58FE795E5FA008CB97B`.
The exact installed PNG/layout and reference are archived under
`Unarmed Magic Casting/Final QM`; the private install manifest now marks QM
final and retains the alternative options. All ten installed custom action
hashes were checked and remain unchanged. Do not replace this approved QM
while developing the next equipment set.

All applicable light-unarmed actions are covered. There is no vanilla WLNBL
sheet; blocking requires a shield. The next development set is light armor
with sword and shield, code **WLD** (`WepChar` maps sword+shield to `d`).
The available `palM_1hsShd_nav_idle` clip has been extracted and directly merged
onto the existing edited Paladin: 193 animated bones match, maximum rest-matrix
difference 1.0129064321517944e-05, with original meshes/skins/nodes preserved.
This is a private body candidate, not an installed armed animation. Grip and
shield attachments still need fitting after equipment selection.

The user requested equipment options before fitting. Local options are:

| Label | File | Appearance |
|---|---|---|
| S1 | `sword_base00.glb` | Plain straight crossguard, silver blade |
| S2 | `sword_base01.glb` | Broad curved crossguard, lighter blade |
| S3 | `sword_base03.glb` | Darker worn blade, narrower guard |
| H1 | `shield_base02.glb` | Round wood/metal shield, gold detailing |
| H2 | `shield_base04.glb` | Red round shield with decorated metal boss |
| H3 | `Shield_S15_Warrior.glb` | Plain wood shield with metal rim and crossbar |

`preview_warrior_equipment.py` renders two sides of all six local GLBs, retaining
original dimensions with one fixed camera scale per category. It changes no
source models. Labelled sword/shield contact sheets and source-hash metadata
are saved locally under `Equipment Options`, also in the private
`paladin-sword-shield/equipment-options` work folder. S1/H2 is the proposed
closest visual match to vanilla; the user's selection remains pending. No
armed sheet has been installed. Equipment models, textures and previews remain
outside Git; only this renderer and notes are committed.

#### H3 red-wood option

The user requested H3 in red. `paint_shield_wood.py` creates the separate
`Shield_S15_Warrior_Red.glb`. The source has one shared PBR material; its existing
metallic texture classifies triangle interiors into wood and metal. The 274 wood
triangles receive a copied material with base-color factor `[1,0.075,0.05,1]`,
giving a dark red finish while retaining the original grain. The 742 metal
triangles keep the original material. Both faces are red; rim, boss, crossbar
and rear fittings remain metal. All 1,016 original triangles, nodes, position,
normal and UV data are preserved. Embedded images are retained byte-for-byte;
only material assignment and additional index buffers change.

The original source remains unchanged, SHA256
`3CE969A5D3F4425A9F51AD97D74A5FA6634DB5952725ADF66C1E414732BFE2BF`.
Red variant SHA256:
`34977AA5B6BF1E98296CC4C81917F52DC2EC0CDDCA21CE7A0522C67186D15F23`.
Front/back views were rendered and visually checked. The red GLB is saved beside
the original local equipment models; `Equipment Options` contains
`H3 Red Shield.png`, `H3 Before and After.png` and validation metadata.
`preview_warrior_equipment.py` now accepts optional explicit model paths after
its output directory to compare variants. No armed sheet or game executable
was changed. User equipment selection remains pending. Only source/notes are
committed; models, textures and previews stay local.

### Selected S1 and red H3: equipped dungeon idle

The user selected `sword_base00.glb` and `Shield_S15_Warrior_Red.glb`.
The first armed test uses `palM_1hsShd_nav_idle` and original WLDAS layout:
ten 768×768 rows, eight directions, 6144×7680, with sidecar
`D1R_SHEET_V1 8 48 96`. The existing body calibration and southeast sun are
retained. Source equipment files and character geometry are unchanged.

`paladin_equipment.py` imports rigid equipment, sets its initial orientation
from native weapon sockets, and parents it to the appropriate hand. It
compensates Blender's bone-tail parenting offset and supports explicit grip
points in **Blender imported mesh coordinates**, not raw GLB axes. This matters
because the importer bakes its axis conversion into these rigid meshes.
`wld_idle_equipment.json` records the selected assets and authored mounts.

S1 uses a 0.75 instance scale (about 1.04 total length), a 10/0/17-degree guard
adjustment, and a grip at imported coordinate `(0,0.16,0)` aligned to
right-hand point `(0,0.05,0)`. H3 retains its source size, rotates its crossbar
90 degrees into the guard stance, and mounts rear grip `(-0.2,0,-0.1)` to the
same local point on the left hand. The original exported sword was oversized
for this stance and the first socket-only mounting sent its blade across the
lower body. That prototype was shown before correction. The original high
shield mounting also extended its shadow beyond the sheet. The final grips
and guard orientation fit without altering body scale, canvas or light/shadow
length. These instance transforms do not overwrite either source GLB.

The ten sampled idle poses retain maximum grip error 1.228781230931777e-07 m;
the sword blade centreline does not intersect the opaque body in those poses.
This is a centreline check, not exhaustive blade-edge collision certification.
Vertical-only floor corrections are derived from body geometry and remain
below 0.00003 m. The renderer's optional equipment path leaves unequipped
references unchanged. The shadow renderer includes tagged rigid equipment
alongside the six opaque body parts; both sword and shield cast moving shadows.

Private production files are under `paladin-sword-shield`. Ten output rows
sample native frames 0,16,...,144. The comparison uses original NN8 WLDAS at
the same cell size, with a separate all-eight-facing idle GIF. Only the first
dungeon-standing action is being replaced; town, movement, attacks, reactions,
blocking and casting for WLD still need their own appropriate motions.

Final output passes all 80 body/equipment and 80 full-shadow cell bounds checks,
with minimum margins 67 and 21 NN8 pixels. The saved equipment profile matches
the production reference exactly. The south/west vanilla comparison and all
eight new facings were visually reviewed before installation. Installed WLDAS
SHA256:
`FCE48255DF020E6E854547C31F70846E3E8D94189A5DDA112F7B636170C3EC1D`.
Local archive: `Sword Shield S1 H3 Red/Dungeon Idle`, including the prior
vanilla PNG, reference, validation, preview GIFs, body GLB and equipped Blender
test scene. The current mirror and install manifest now record eleven custom
actions and the selected equipment. All ten previous unarmed sheet hashes are
unchanged, including approved final QM. Only WLDAS was replaced. No executable
or build-version change. In-game idle appearance still needs review with a
light-armored warrior holding sword and shield in a dungeon; this does not yet
replace the other WLD actions. Models, scene, textures and previews stay local.

#### Shield forearm mount correction

The user identified that the shield sat off the arm. The prior hand-centred
anchor kept a handle point fixed but did not align the rear brace with the
forearm. The corrected profile parents H3 to **forearm.L**, with its rear
crossbar aligned along the forearm rather than inheriting the weapon socket's
rotation. The imported mesh X axis maps to negative forearm Y; mesh front Z
maps to forearm X. The hand remains the grip target through optional
`grip_target_bone = "hand.L"`. `paladin_equipment.py` now supports this separate
grip target and an authored local basis. Older profiles retain their defaults.

The shield instance is fitted at 0.92 source scale (about 0.70 diameter) so the
rear brace sits closer to the arm. The original shield GLB, sword, body meshes,
native animation and hand pose are unchanged. Across all ten idle samples the
rear-brace/forearm axes remain aligned (reported angle error 0 degrees), and
maximum handle-to-hand target error is 4.054786402718884e-06 m. A close rear-view
render was visually checked for arm contact, alongside south/west comparisons
and all eight facings. This corrects the mount rather than merely translating
the floating shield in screen space.

All 80 body/equipment and 80 full-shadow bounds checks pass, with minimum
margins 67 and 3 NN8 pixels. Original 6144×7680 dimensions, fixed registration,
body scale, southeast sun and full moving shadows are preserved. Installed
WLDAS SHA256:
`5029C282F719A0C919E8BF28156BAE39AA8357F5C0B696BF89CAC1067C54F8A6`.
Production reference and frames are now under
`paladin-sword-shield/forearm-fix`; use that reference for subsequent work.
The archive is `Sword Shield S1 H3 Red/Forearm Mount Fixed`, including the
equipped Blender test scene, contact close-up and `Previous Hand Mount` backup.
The before/after GIF retains its generic pipeline filename but labels the
previous and corrected mounts, not vanilla. The mirror and manifest select the
correction; all ten unarmed hashes remain unchanged and QM stays final. Only
WLDAS was replaced. No executable or version change. Live gameplay still needs
visual review; models and renders remain local.

#### Sword seated inside the closed hand

The user approved the forearm shield mount and identified that S1 touched the
hand without passing through its grip. Close-ups confirmed the old anchor was
near the wrist and the forced blade-up axis did not match the finger opening.
The corrected S1 mount uses native `weapon.R` orientation with a -90-degree
imported Z-axis rotation: its handle crosses the closed-finger opening along
the native socket X axis. The leather-grip centre is imported coordinate
`(0,0.075,0)`, aligned to hand-local `(0.0425,0.0825,-0.002)`. The old X-axis
correction and authored guard rotation are removed. This gives the native
outward/downward sword guard while placing the leather wrap through the palm,
between thumb and fingers, with the pommel outside the hand.

Reviewed close-ups from three sides, including the leather section rather than
the metal pommel. Finger/hand poses and all body animation remain unchanged;
only the rigid sword mount changes. Across ten idle samples, maximum sword-grip
anchor error is 1.2644054553268208e-07 m. The blade centreline clears the opaque
body in all samples. This is not exhaustive blade-edge collision certification.
The approved shield configuration matches the previous reference exactly,
with the same forearm parent, basis, source scale and grip target.

`wld_idle_equipment.json` records the corrected mount. Private production files
are under `paladin-sword-shield/sword-grip-fix`; use this reference for further
equipped work. Contact previews compare the old wrist contact with the new
leather-in-palm fit, plus both sides of the corrected grip. The idle comparison
labels previous/new sword grips rather than vanilla.

All 80 body/equipment and 80 full-shadow bounds checks pass, with minimum
margins 67 and 3 NN8 pixels. Original dimensions, fixed anchor and body scale
remain unchanged. Current WLDAS SHA256:
`3F9EE94085B40D4ECEA89A6CAA41022568472C4BF5994736DA9FF8BF906F3C0D`.
The local archive is `Sword Shield S1 H3 Red/Sword Grip Fixed`, with close-ups,
an equipped test scene and `Previous Sword Mount` backup. The current mirror
and manifest select the corrected grip and record the shield as user-approved.
All ten unarmed action hashes remain unchanged. Only WLDAS was replaced. No
executable/version change. In-game visual review remains outstanding; all
models, images and diagnostic pose data stay local.


### Complete light-warrior equipment inventory

The batch tools build the actual WLD (sword/shield), WLS (sword), and WLU
(shield) inventory: 10 + 9 + 10 sheets, 3,104 stored directional frames.
Death uses the existing shared unarmed sheet; WLS has no block sheet. Original
CL2 headers and NN8 dimensions are checked before planning. AT has 16 rows in
128-pixel logical cells; other equipment sheets use original 96-pixel cells.
All three equipped casting sets store 20 rows, including LM (the previously
approved unarmed LM stores an extra row). Direction order remains
S, SW, W, NW, N, NE, E, SE.

`capture_equipment_mounts.py` freezes the approved S1 leather-in-palm and red
H3 forearm transforms from the accepted scene. `prepare_equipped_sources.py`
selects existing native 1hsShd walk, weaponAttack, flinch_B, and withstand clips
and verifies their skeleton against the edited model. No source clip is
invented. `equipped_set_plan.py` plans 17 canonical renders and 12 exact
copies/aliases. Original sheets show the sword put away for town and casting;
shield remains visible. Approved unarmed town/cast sheets supply the sword-only
versions, with LM cropped to its actual equipped 20-row layout.

`author_equipped_motion.py` appends sampled animation tracks without changing
meshes, skin bindings, nodes, materials, images, or the original binary data.
The approved shortened unarmed gait supplies core/legs; native equipment arms
supply their weapon motion. Finger poses maintain the accepted grips. Per-arm
IK can lower the guard using a native elbow pole and fixed limb lengths;
pose blending and wrist-motion controls keep gestures inside the existing
canvases. Sword contact is aligned to game attack frame 9. Casting uses the
approved Gizmo body motion, fire bubble, lightning, and final QM option 2.

`preflight_equipped_sets.py` checks every authored pose in eight directions,
including full southeast-projected equipment shadows and the sword centreline
against opaque body surfaces. This is not exhaustive blade-edge collision
certification. Small conservative numerical margins are followed by strict
raster body/shadow bounds checks; no clipped image is accepted. The renderer's
optional root-anchor frame is zero for these sampled clips; legacy references
keep their previous frame-one default. Shadow projection uses the same formula
with vectorized vertex extraction. Geometry scale, fixed tile anchor, lighting,
shadow length, and original sheet/cell dimensions remain unchanged.

Run preflight again to retry only unsafe motions. `build_equipped_sets.py`
renders validated motions with two local workers, caches by inputs/tool hashes,
then validates the complete 29-sheet pack and creates three all-action GIFs plus
all-action/eight-direction grids. `install_equipped_sets.py` requires the full
report and unchanged starting live hashes; it archives prior installed files,
checks all 11 existing custom sheets, installs the complete pack, updates the
private manifest/mirror to 39 custom sheets, and verifies the executable hash.
It does not build or replace the executable. Asset-only work retains 0.4.1-pre.
All artwork, extracted tracks, private recipes, reports, scenes, and previews
remain outside Git. In-game appearance requires a gameplay review after reload.


The completed local pack passed all 17 canonical render checks and all 29
original-layout file checks, covering 3,104 stored directional frames. Installed
under the existing HD warrior folders, with 28 changed PNGs and the exact approved
WLDAS retained. The private manifest/mirror now contains 39 custom sheets. All
11 previous custom hashes, including final unarmed QM option 2 and shared death,
remain unchanged. Exact previous installed files and all-action GIF/grid reviews
are archived in `Light Warrior Equipment Sets 2026-10-25` beside the local model.
No gameplay session was used to certify the newly installed actions.

The sword attack uses a compact native gesture (full torso motion, arm excursion
0.1, 0.05 m guard adjustment), retaining the frame-9 contact. The combined hit
reaction uses half the native torso excursion and a 0.1 m guard adjustment to
keep its head/equipment shadow inside the fixed cell. Shield-only block uses a
0.25 native arm blend and 0.15 m lower guard. These are animation adjustments;
mesh dimensions, limb lengths, sword/shield scale, and projected shadow length
are unchanged. Full-resolution raster checks determine acceptance after the
geometry preflight; an initial combined hit render was rejected for touching
an edge and was replaced before installation.


### Attack motion review: native sword and forward shield smash

The user rejected the compact sword cut and the raised-guard shield attack.
Those experimental revisions were not installed. The user selected the complete
native sword motion, including the body lunge, with only timing/alignment changed.
This supersedes the previous 0.1 arm-excursion attack choice. Available exact local
clips are `palM_1hsShd_attk_swordAndBoard`,
`palM_1HSShd_attk_weaponAttack`, and `palM_1hsShd_attk_shieldBash`.
All 330 animation names were inspected; there is no separate clip named 1h swing.

`equipped_attack_recipe.py` now retains all sword pose channels. Native
swordAndBoard frame 8 is game frame 9; native samples are
0,1,2,3,4,5,6,7,8,10,40,43,46,50,55,59. The long native hold is skipped.
Horizontal root normalization is a constant translation, not a pose blend.
Comparison of both authored sword clips with all sampled native rotation,
scale, and non-root translation channels found zero error. Root translation
changes by the same (0.2552620769, 0, 0.0846653283) metres in every sample.
The existing renderer removes horizontal root travel and grounds the sampled
poses for tile-based play. No limb, wrist, body-lunge, or weapon-scale edits
are applied to the selected sword motion. Preflight must not automatically
attenuate attacks marked preserve_attack_motion.

A root-aligned, full-shadow clipping inspection rendered S/W/NW, 16 frames each.
Raw body and shadow overscan images were checked for complete capture before
compositing. At original 128-pixel logical attack dimensions, all 48 body/sword
cells fit. The full projected shadow extends up to 140 NN8 pixels (17.5 logical
pixels) outside the cell. Diagnostic GIFs mark the original cell in blue,
shadow overflow orange, and body/sword overflow pink. They are local in
`equipped-sets/attack-refinement/native-clipping`. Do not claim this raster
inspection covers the five other directions.

Padding is a separate user choice; it has not been authorized or installed in
this revision. A private 176x144 logical canvas with anchor (88,136) was tested
numerically in eight directions as a candidate. It preserves art scale and the
world foot anchor. The current executable's existing layout loader accepts
rectangular, padded cells and explicit anchors; no engine replacement is needed.
`refine_equipped_attacks.py` accepts an optional local sword-canvas JSON with
logical and anchor arrays. Without that explicit profile, original-cell
preflight intentionally rejects clipped native shadows. The optional profile
applies only to sword-bearing AT sheets. Rendering a padded candidate is not
an authorization to install it.

The first native shieldBash export holds a charging/guard pose after root travel
is removed; merely blending into it read as blocking. The forward-smash
prototype starts from the accepted equipped guard with the unused right arm
relaxed. It retracts the left hand, drives it forward and across the body with
two-bone IK, and recoils, maintaining the forearm shield mount and closed grip.
A small native chest/hip/leg weight shift supports the hit. It uses the original
128-pixel cell and keeps its frame-9 impact. Node overlays, per-frame overlay
weights and hand offsets are authored animation controls; mesh/skin/node/image
records remain untouched. Its local render is `shield-forward-smash` and remains
subject to visual review. The previously rejected raised-guard plan is marked
superseded to prevent accidental installation.

`install_equipped_attack_updates.py` verifies all current custom hashes and
allows only three validated AT replacements, with backups and receipts. It
rejects superseded plans, altered sword-pose recipes, and shield recipes without
a forward hand drive. It does not install during rendering/preflight. At this
review checkpoint all 39 installed custom hashes still match the prior manifest;
no attack revision or executable/version change has been installed.


### 2026-10-25 shield wrist review checkpoint

The selected shield attack remains `palM_1hsShd_attk_shieldCharge_3units`, sampled to 16 game rows with the existing two-pass smoothing and contact row 8. The shield now follows the approved hand-relative mount instead of a world-locked orientation. At the user's request, only `hand.L` rotation is corrected to make the shield plane vertical during the strike; shoulder, elbow, reach, all translations and all other body animation channels remain unchanged. This replaces the rejected independent world-upright shield constraint. A private evaluated-mesh check found zero shield/head triangle intersections in 61 quarter-frame samples spanning rows 0 through 15. All 575 non-wrist/non-equipment animation channels match the prior follow-hand preview exactly. This is a preview checkpoint, not an installed WLUAT update; do not treat the earlier rejected shield previews as approved. The two padded native sword attacks were already installed separately; retain them. Proprietary models, clips, rendered sheets and previews remain outside Git.


### 2026-10-25 shared shield grip correction

The H3 red shield was reversed **within its face**, not front-to-back. Inspection of the original mesh's rear straps confirmed that the former mesh-local hand anchor `[-0.2, 0, -0.1]` was at the large-strap end. The small handgrip is at `[0.23, 0, -0.1]`. The corrected mount turns 180 degrees about the measured shield-plane normal, preserves the outward boss face and the existing hand target, and places the larger strap toward the elbow. `shield_mount.py` records this authored numeric adjustment as `small-handgrip-180-v1`; it is idempotent and changes neither scale nor body animation.

All 20 WLD/WLU sheets require this correction, including the formerly copied WLDAS combined idle. Fourteen distinct render jobs supply those 20 sheets through six aliases. The nine WLS sheets are copied from the current installed manifest, including the already installed padded native sword attack. The ten WLN sheets and shared unarmed death remain unchanged. WLDAT retains the complete native swordAndBoard motion, its approved timing, contact at game frame 9, and the existing 176x144 logical attack cells. WLUAT uses the selected native `palM_1hsShd_attk_shieldCharge_3units` bash with the requested smoothing and wrist-only tilt; shoulder, elbow, reach and other body animation channels remain unchanged.

The corrected grip adds a small amount of shadow extent in AW/WL and WLD BL. WLD AW, WLU AW, WLD WL, WLU WL and WLD BL therefore receive one transparent logical pixel on each horizontal side: 98x96 logical cells, anchor `[49,96]`. This changes the source rectangle only; the character scale, on-screen foot anchor, southeast sun and full shadow stay unchanged. No other non-attack cell dimensions change.

Validation covers all 14 animations and all eight raster directions. The evaluated-mesh mounting audit checks 254 poses, including quarter-frame samples in both attacks: zero shield/head triangle intersections, zero poses with the large strap on the hand side of the elbow, and maximum grip-target error 0.00884 meters during the unchanged native sword swing. Other states remain within approximately 0.000005 meters. The correction preserves the shield face normal, grip target and scale mathematically; recapturing the corrected idle binding matches the authored profile within 0.0000003. The public preparation script reproduces the active 29-sheet inventory and all 14 corrected references exactly.

Reproduce using the existing private equipment plan, native sword revision plan, wrist-bash revision plan, combined-idle body model and combined-idle reference. `prepare_shield_mount_updates.py` accepts those five inputs plus a new private work directory; `audit_shield_mounts.py` prepares/checks it in Blender; `build_equipped_sets.py render` and `validate` render and validate all 29 target sheets; `install_shield_mount_updates.py` backs up and replaces only the 20 shield sheets after validating the complete current manifest. The installer rechecks all 39 custom sheets and the executable, updates both manifest copies, and rolls back on failure. The engine remains 0.4.1-pre because this is an asset correction using the existing loader. Models, animations, rendered sheets, GIFs and backups remain private and outside Git.

Installation completed: all 20 corrected WLD/WLU sheets are installed in `D:/Games/Diablo/HD/plrgfx/warrior`. Exact previous-sheet backups, final art, the 254-pose strap audit, the complete 29-sheet pack report and updated manifest are in the private asset archive `Light Warrior Equipment Sets 2026-10-25/Shield Grip Correction`. All 39 installed custom-sheet hashes were verified; the nine WLS and ten WLN sheets are unchanged. The executable SHA-256 remains `52B3E407DE77ABC1E0CA5B4D567736388BE4046B31BA036269F615D0941AA28B`. The corrected northwest bash steps and GIF are included with the private review artifacts.


### 2026-10-25 approved shield baseline and next mace set

The user approved the installed shared shield-grip correction. Keep that setup as the baseline for every later shield-bearing weapon set.

The next prepared equipment family is the light-armored warrior with a blunt weapon: WLM is mace without shield and WLH is mace with shield, confirmed against Source/player.h WepChar. The supplied vanilla NN8 directories contain nine WLM and ten WLH action sheets. The local male Paladin animation collection contains matching one-handed attack families; there is no separately named mace animation family. Inspect suitable native one-handed motion with the chosen model before selecting the strike.

Two existing local candidates were rendered front and back at the same camera scale without editing or scaling the source models: M1 is mace_base03.glb (broader worn flanged head, red-brown handle; approximately 1.0103 m long), and M2 is mace_base07.glb (slimmer pointed head, dark handle; approximately 1.0287 m long). The candidate previews and hashes are private in warrior-3d/mace-options. Model selection is pending. No mace sheet has been installed, and all 39 approved custom sheets remain unchanged. The equipment preview tool now labels explicit mace, axe, bow and staff inputs by family and uses weapon framing instead of the smaller shield camera.


Both mace candidates were then fitted for comparison at the approved 0.75 weapon scale with mesh-local grip `[0,0.18,0]` on the wrapped handle. The existing body animation and corrected shield mount remain unchanged. Each candidate has a ten-frame idle and sixteen-frame complete native swordAndBoard swing rendered from South, West and Northwest. These are explicitly partial-direction previews, not installable mace sheets. All 156 body/shadow view cells pass full-alpha capture checks. A common preview rectangle preserves apparent character scale between idle and attack; the selected-direction assembler writes GIFs/contact images and validation only, never a game sheet. `prepare_mace_previews.py`, `render_equipment_previews.py`, `assemble_equipment_preview.py` and `compare_equipment_previews.py` reproduce the private comparisons. The user requested both options in context; selection is still pending. All 39 installed custom sheets are unchanged.


### 2026-10-25 selected M1 light-warrior mace sets

The user selected M1 (`mace_base03.glb`) for both light-armored blunt-weapon layouts: WLM (mace alone) and WLH (mace plus the approved H3 red shield). `prepare_mace_sets.py` derives the complete 19-sheet inventory from the supplied vanilla NN8 PNGs and original CL2 frame counts: nine WLM actions and ten WLH actions. It reuses nine approved body animations unchanged, replaces only the rigid right-hand weapon using the fitted `[0,0.18,0]` grip at scale 0.75, and copies ten approved town/casting sheets where vanilla has no weapon in hand. No additional death or mace-only block sheet exists; shared unarmed death remains in use.

The actual warrior animation table confirms frame-9 attack contact for both `maceActionFrame` and `maceShieldActionFrame`. The complete native swing, previously selected timing, short-stride walking, body size, foot anchors and southeast sun remain unchanged. The approved 176x144 attack canvases are retained for both mace attacks. Shield-bearing walks/block retain the existing narrow transparent shadow border; no new character scaling or arm changes are applied. The selected fire/lightning/magic effects and corrected shield grip are preserved.

`audit_mace_sets.py` checks all nine existing body motions, the full projected-shadow bounds, the rigid right-hand grip, and mace intersections with torso, head, legs and boots (the gripping glove is intentionally excluded). All 172 tested poses, including quarter-frame attack transitions, have zero weapon/body triangle intersections; maximum grip-target error is below 0.0000003 meters. `build_equipped_sets.py` now accepts the explicit 19-sheet light-mace family in addition to the original complete 29-sheet sword/shield pack. The targeted mace installer requires all nine geometry audits, all-direction raster validation and an unchanged current manifest; it backs up all 19 former game sheets and any prior layout/mirror files, preserves existing custom art and the executable, and supports rollback. Models, animation buffers and rendered output remain private.

Installation completed: all 19 selected M1 WLM/WLH sheets are installed in `D:/Games/Diablo/HD/plrgfx/warrior`. The complete pack contains 2,064 stored directional frames. All 58 installed custom-sheet hashes were verified, including the 39 unchanged earlier custom sheets. Exact previous game/mirror files, final art, pose audit, pack report, updated manifest and all-action GIF/eight-direction reviews are archived privately under `Light Warrior Mace M1 2026-10-25` beside the local model. The executable remains 0.4.1-pre with SHA-256 `52B3E407DE77ABC1E0CA5B4D567736388BE4046B31BA036269F615D0941AA28B`. No gameplay session was used to certify the new mace states; they are ready for in-game review.


### 2026-10-25 selected A1 two-handed axe

The user selected A1 (`twoHandAxe_base01.glb`), the classic double-bladed axe, for WLA. The real warrior animation table requires twenty axe attack frames and contact at game frame ten. The existing private Paladin collection supplies `palM_2HM_nav_idle`, `palM_2HM_attk_basic`, `palM_2HM_nav_walk` and `palM_2HM_reac_flinch_B`; all 193 animated joints match the edited character with maximum rest-matrix difference 0.0000101291. Character geometry, materials, images and skin bindings remain unchanged. Walking uses the previously approved 0.6 leg-rotation/0.5 pelvis short-stride treatment.

The axe is attached directly to the native animated `weapon.R` socket with the existing -90-degree mesh-axis correction at native equipment scale 1.0. This preserves the source's sliding right-hand grip and support-hand separation/regripping. The rigid dual-palm prototype was rejected, marked superseded and never installed; its extra attachment implementation was removed, leaving the previously approved generic equipment helper unchanged. The twenty attack samples place native frame twelve at game frame ten and skip the long post-contact hold while retaining recovery. The first three samples blend from idle to avoid a starting-pose pop; the native final pose already returns to the two-handed idle. No arm IK, limb scaling or body pose attenuation is used.

A1's spare wooden butt initially intersected the torso briefly during wind-up. `fit_two_hand_axe.py` creates a separate private GLB, shortening only the unused lower end from 0.365299 to 0.29 meters (approximately 7.53 cm), by compressing the last section beyond 0.24 m. Ninety-eight position vertices change only along that axis. The axe head, other positions, topology, normals, UVs, materials, texture images and the original supplied asset remain unchanged; the original SHA-256 remains `6704b25f05a6225c249736e4ca2412704274c719e8a9672e6f00c78c696b2f66`. The fitted model and exact fitting report stay private.

`audit_axe_sets.py` authors and checks four weapon-bearing actions and derives minimum transparent padding from all body and full southeast-shadow bounds in eight directions. The resulting logical cells/anchors are AS 158x101/(79,101), AT 182x152/(91,128), AW 156x101/(78,101), and HT 164x102/(82,102). This preserves the original body scale and world foot anchor; the extra space is transparent. All 101 checked poses, including quarter-frame attack transitions, have zero weapon/torso/head/leg/boot triangle intersections (gripping gloves excluded). The right-palm shaft proximity remains within the native hand width; support-hand motion is preserved rather than forced onto the haft in every pose. There are no axe-specific death or block sheets. Five already approved town/casting sheets are copied unchanged from WLS, where vanilla hides the weapon.

The source planner/auditor/installer and full-pack validator now support the explicit nine-sheet light-axe family and its frame-ten contact. The native clip preparer rejects cached body meshes/bindings/image buffers that differ from the current character. Equipment option cameras now fit the largest model in each category without per-model zoom; wide partial-direction previews and axe comparisons are supported, and superseded previews cannot be rendered accidentally. No copyrighted models, animation buffers, sheets or GIFs are included in Git.

Installation completed: all nine A1 WLA sheets are installed in `D:/Games/Diablo/HD/plrgfx/warrior`, covering 1,056 stored directional frames. All 67 installed custom-sheet hashes were verified; all 58 previous custom sheets and the executable remain unchanged. The largest retained decoded image is 67.54 MiB, below the existing PNG loader 128 MiB entry guard. Backups, final sheets, fitted A1 GLB/fitting report, padding data, audits and all-action/eight-direction reviews are saved privately under `Light Warrior Axe A1 2026-10-25`. The existing executable remains 0.4.1-pre with SHA-256 `52B3E407DE77ABC1E0CA5B4D567736388BE4046B31BA036269F615D0941AA28B`. No gameplay session was used to certify the new axe state. Bow and staff remain the unfinished light-warrior weapon families.


### 2026-10-26 edge-first axe orientation correction

The user identified that A1 was travelling broadside through the cleave. The mesh is now rotated 90 degrees about its own longitudinal Y/haft axis before the existing native socket-axis transform: local basis `[[0,0,1],[0,1,0],[-1,0,0]]`. Every character/body/hand animation channel and the haft centerline remain unchanged. This is applied consistently to AS/AW/AT/HT and is now the default in the axe planner. `revise_axe_orientation.py` prepares an explicit revision from the current manifest without reauthoring body animations; the axe auditor supports that mode.

`check_axe_edge_orientation.py` compares the blade-face normal against perpendicular-to-haft head velocity at seven samples across the main cut. Original broad-face alignment was 0.900–0.997 (1 means broadside-first); the corrected values are 0.073–0.436 (0 means edge-first). All 101 body-intersection/grip samples still pass. Transparent canvases were refitted without changing world foot anchors: AS 158x101/(79,101), AT 184x149/(92,128), AW 150x103/(75,103), HT 168x101/(84,101).

The corrected complete nine-sheet pack was installed with backups under the private `Light Warrior Axe Edge First 2026-10-26` archive. Four weapon-bearing PNGs changed; five town/casting copies and all 58 other custom sheets are byte-identical. All 67 live custom hashes and the original executable hash were verified. The revision installer requires the successful edge-orientation measurements and preserves exact backups. The user subsequently requested an audit and correction of carried/stowed weapons and shields in town idle/walk sheets; that work follows this installed edge-first baseline.


## 2026-10-26 â€” equipment restored in light-warrior town sheets

Supersedes earlier notes describing equipped town standing/walking as unarmed. GetPlayerWeaponGraphic redirects town casting only; standing and walking retain the equipped variant. Ten sheets are now installed: WLS/WLD/WLM/WLH/WLA ST and WL. Sword and original leather scabbard sit on the left, shield-side hip; mace hangs head-down on the right in an original belt frog; axe is carried low in the right hand. Shield variants retain the approved corrected shield mount. Unarmed and shield-only town sheets, original bow/staff, and other armor remain unchanged.

The approved body scale, short stride, brightness and southeast sun are retained. Axe town carry steadies only the right wrist and closes the fingers; shoulders, elbows and gait are preserved. All combat/casting sheets, including the edge-first native axe swing, are unchanged. Explicit root_anchor_frame=0 aligns resampled town bodies and shadows. Transparent canvas padding retains model scale and the foot anchor.

Validation: all ten sheets and 1,120 directional cells passed body/shadow bounds checks; all 140 animated poses passed the equipment intersection audit. A clean planner reproduction matched every fitted model hash and mount matrix. Installation verified all 67 custom sheet hashes and preserved the other 57. Executable remains 0.4.1-pre, SHA256 52B3E407DE77ABC1E0CA5B4D567736388BE4046B31BA036269F615D0941AA28B. This is an installed/render-validated result; a new interactive game session has not been certified.

Private archive: I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Town Equipment 2026-10-26. It contains previous installed sheets, final sheets/layouts, equipment, actual mount transforms, audit reports and reviews. Assets and generated sheets remain outside Git.

Rebuild: build_town_props.py creates original scabbard/frog props; prepare_town_equipment.py prepares the ten jobs from existing approved inputs; audit_town_equipment.py checks every pose and canvas; build_equipped_sets.py renders/validates; install_town_equipment.py installs with backups and rollback. Future sword/shield, mace and axe planners preserve each approved equipment-specific town sheet rather than reverting to an unarmed alias. Missing private inputs must be supplied from the existing archive, never fabricated.


## 2026-10-26 â€” native sword sheathe endpoint and back-mounted town shield

Supersedes the forearm-mounted town shield in the preceding revision. WLD, WLH and WLU now stow H3 on the back for ST/WL. WLS/WLD sword and scabbard use the weapon.R socket at the exact last frame (54 at 30 fps) of palM_1hsShd_event_sheathe from the existing palm_all_anims.glb. That final frame is a placement reference only; the sheathing event itself is not played in town. The source event has no shield mesh; H3 is mounted independently to chest with its red/boss face outward and straps toward the back. No combat shield mount changes.

The wider custom outfit requires a rigid sword/scabbard clearance offset of (+0.10,+0.18,-0.08) in the initial town-body world axes, converted to pelvis-local space; the native final-frame angle is retained. Eight town sheets change: WLS/WLD/WLH/WLU ST and WL. Shield variants use the already approved relaxed town body, rather than holding the empty combat shield arm up. Existing mace-only/axe town sheets, all combat/casting, scale, stride, density, anchors and southeast shadows are preserved.

Validation covers 112 animated poses, including shield intersections against every opaque body part (the forearm-contact exception does not apply to a back shield), and 896 directional body/shadow cells. All pass without equipment/body intersections or cell-edge clipping. Installation verifies all 67 custom sheet hashes, preserving 59 other sheets and the 0.4.1-pre executable. Interactive gameplay still needs user confirmation.

Reproduce: select_paladin_animation.py selects the exact named clip; merge_paladin_walk.py attaches it to the existing edited character without replacing meshes/skins/nodes; revise_town_stow.py takes the previous town plan, merged event GLB and new private work folder. Then audit_town_equipment.py, build_equipped_sets.py render/validate, and install_town_equipment.py. The installer rejects the older forearm-town recipe after this revision is installed. Private native reference, equipment, previous/final sheets, transforms, audits and reviews are archived under I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Back Stow 2026-10-26. No proprietary data is committed.


Back-stow fit: fit_back_shield.py makes a private stowed H3 variant with negative-normal depth compressed to 20 percent, folding its forearm loops. The positive-normal face/boss vertices and the source combat asset remain unchanged. Supply this GLB as BACK_SHIELD.glb before NEW_WORK in revise_town_stow.py. The rigid stowed shield is centered at world (0,0.245,1.22) in the initial approved town pose, mounted relative to chest. This removes the high, floating placement of the first uninstalled prototype. Final full-pose audits include the folded loops; no strap/body contact exception is used.


## 2026-10-26 â€” closer town shield; rear bands may overlap the body

User-authorized correction: rear shield bands may clip into the body. The town H3 mount moves 0.075 m inward (initial world Y 0.245 to 0.170); height, scale, facing, sword placement and body animation stay fixed. It uses the original red shield with its full rear bands rather than the folded-loop derivative. WLD/WLH/WLU ST/WL are refreshed; WLS town sheets are reused unchanged.

back_shield_contact.py classifies disconnected source-mesh components that extend behind local Z=0 as rear bands, asserts those components remain below the front-face depth, and excludes only their triangles from the body-intersection rejection. Face, boss, wood and rim geometry remain strictly checked. The exemption is opt-in on the back-shield reference only and never affects combat mounts. Full-pose preflight passes at this closer offset. Pack validation covers 896 directional cells, including 224 unchanged sword-only cells. The installer now records actual changed hashes separately from the installed bundle, preserving 61 other custom sheets and the unchanged executable. New private archive: I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Close Back Stow 2026-10-26. Pass the original Shield_S15_Warrior_Red.glb as BACK_SHIELD to revise_town_stow.py; the prior folded-loop fit is superseded for town use.


## 2026-10-26 â€” town shield centered in the chest frame

The earlier world-aligned plane was not aligned with the turned idle torso. The stowed shield now uses the chest's anatomical frame: local X backward, local Y along the spine, local Z across the shoulders. Its face is parallel to the back, with its geometric rim center on local lateral Z=0 (including compensation for the source mesh's 0.005992 local-X center offset). The mount center is 0.22 backward and -0.025 along the spine relative to chest. This replaces the previous world-axis placement; the close fit, original rear bands/body-overlap allowance, source shield scale and sword placement are retained.

All eight bundled town sheets pass full-pose preflight; only WLD/WLH/WLU ST/WL hashes change. WLS town sheets are reused unchanged. Install archive: I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Centered Back Stow 2026-10-26. All 67 installed custom hashes are verified, with 61 other sheets and the executable preserved. The installer stores the actual chest-local mount transforms and previous sheets. No proprietary assets are in Git.


## 2026-10-26 â€” sheathed sword broad face toward thigh and belt attachment

The sheathed S1 and its scabbard now roll together around the preserved native shaft axis. The broad-face normal points outward from the left thigh, so the flat side rests toward the thigh rather than the edge. The existing rear/inward belt hanger now faces the belt. A -0.03 world-Z rigid assembly adjustment lets the upper end of its leather hanger meet the belt while clearing the idle hand and walking armor; body motion and native shaft angle remain unchanged. No combat sword mount changes.

revise_town_sword.py prepares four WLS/WLD ST/WL updates from the existing centered town plan. Full-pose audits pass for sword, scabbard and body; the hanger's intentional belt contact retains its existing exception. WLU/WLH town sheets and centered shield transforms are reused unchanged. The eight-sheet validation bundle includes four cached sheets; only four installed hashes change, preserving 63 other custom sheets and the executable. Private archive: I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Flat Town Sword 2026-10-26.

The installer saves town_sword_roll_revision with the exact pelvis-local mount. Subsequent revise_town_stow.py runs reuse that approved mount; revise_town_sword.py also reuses it when already installed so repeated planning cannot lower or rotate it cumulatively. Source models/textures remain unchanged and outside Git.


## 2026-10-26 â€” hilt/guard only in town; shield another 8 cm closer

Latest user direction supersedes the custom sheath: remove the scabbard and belt hanger entirely, keeping only the D4 sword handle and guard close to the hip. make_town_hilt.py creates a private town-only S1 derivative, cuts away the blade below raw Y=-0.035, and caps the cut. Source sword geometry/materials on disk and all combat sheets remain untouched. The approved flat sword mount is retained for this hilt; no floating scabbard or hanger is rendered.

The centered shield mount moves inward along chest-local X from 0.22 to 0.14. Rear-band/body overlap remains allowed, while shield face, rim and boss are checked against every opaque body part through all town frames. Full preflight passes at the new offset. Town WLS/WLD/WLH/WLU ST/WL form the eight-sheet update: WLS/WLD gain the hilt-only asset, and all three shield variants gain the closer shield. All other 59 custom sheets and the executable are preserved.

revise_town_hilt.py applies the appearance to an existing stow plan. The installer records town_hilt_only_revision with an archive-local asset path; future revise_town_stow.py plans reuse the hilt and omit the sheath/hanger, and the installer rejects an attempted reversion to the older sheath recipe. Private source derivative, fit metadata, backups, final sheets/layouts, native reference, audits and reviews are archived at I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Town Hilt Close Shield 2026-10-26. All proprietary artwork remains outside Git.


## 2026-10-26 â€” full D4 town sword restored, no custom sheath

Latest approved behavior restores the complete original S1 sword, including its blade, in WLS/WLD ST/WL. The hilt-only interpretation is superseded. The custom scabbard and hanger stay removed; the approved flat orientation/hip mount and closest centered back shield stay unchanged. restore_town_sword.py replaces only the town hilt instances with original sword_base00.glb, reusing the other four bundle renders. Full-pose audits pass. Four sheet hashes change; 63 other custom sheets and the executable are preserved.

The installer removes town_hilt_only_revision and saves town_bare_sword_revision with the complete sword's archive-local path. Future stow planning retains the full blade without a sheath and rejects accidental reversion to hilt-only/sheath recipes. Private archive: I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Full Sword No Sheath 2026-10-26. Original D4 files and combat sheets remain intact; no proprietary assets are committed.


## 2026-10-26 â€” sword moved up along the user's arrow

The complete town sword slides 0.05 m toward its hilt along its existing shaft axis in WLS/WLD ST/WL. Rotation, scale, broad-face orientation, full blade, no-sheath appearance and closer centered shield are retained. No sideways clearance offset is applied. All idle/walk poses pass body-intersection and full-shadow bounds checks at this translation.

raise_town_sword.py prepares the four changed sword sheets and reuses the other four bundle renders. It stores the new pelvis-local mount in town_sword_roll_revision, so future stow rebuilds retain the raised position. Translations are stored in Blender's float32 precision for repeatable rebuilds. Four sheet hashes change, preserving 63 other custom sheets and the executable. Private archive: I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Raised Town Sword 2026-10-26. Models/sheets/reviews stay outside Git.


## 2026-10-26 â€” another 5 cm sword raise (10 cm cumulative)

The complete town sword moves another 0.05 m toward the hilt along the same shaft, for 0.10 m cumulative from the initial low mount. At the exact second raise the guard intersects eight armor triangles in walking row 2; a 0.01 m outward broad-face-normal clearance removes that contact. Rotation, scale, body animation, full blade, no-sheath appearance and closer centered shield are preserved. All full-pose/body/shadow preflights pass with this clearance.

raise_town_sword.py now accepts optional OUTWARD metres after the shaft distance, defaulting to zero for existing recipes. This update uses the first raised plan as input with 0.05 shaft and 0.01 outward. The authoritative float32 mount is saved for future stow rebuilds. Four sword town hashes change and 63 other custom sheets/executable remain intact. Private archive: I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Town Sword Raised 10cm 2026-10-26. No proprietary assets are in Git.


## 2026-10-26 â€” sword closer to the hip, raised height retained

The town sword moves 0.03 m inward and 0.02 m forward in the initial town body's world frame, with zero vertical shift. This fit brings it toward the body without changing rotation, scale, the raised height or the full-blade/no-sheath appearance. The small forward adjustment avoids armor contact during walking. All full-pose intersections and shadow bounds pass; the shield and body animation are unchanged.

fit_town_sword_hip.py converts that horizontal translation to pelvis-local space and prepares WLS/WLD ST/WL. The new float32 mount is stored in town_sword_roll_revision for subsequent stow rebuilds. Four sheet hashes change, with 63 other custom sheets and the executable preserved. Private archive: I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Town Sword Close Hip 2026-10-26. Artwork remains outside Git.


## 2026-10-26 â€” equipment stow standard: one hand at hip, two hands on back

Approved standard: retain the current complete one-handed weapon at-hip treatment. Two-handed weapons use the last frame of palM_2HM_event_sheathe as the back-stow reference. The exact animation exists in the local palm_all_anims.glb; its final frame is 49 at 30 fps. The event is a placement reference, not a town animation to replay.

prepare_two_hand_back_stow.py attaches the native weapon.R endpoint relative to chest, then applies the selected A1 axe's existing 90-degree haft roll so its broad head lies across the back. Native socket position, shaft angle and axe scale are retained without a clearance translation or source mesh changes. It uses the approved relaxed town idle/walk body with free hands. WLAST and WLAWL replace the prior low hand carry; combat/casting and all one-handed sheets are unchanged. The same event/endpoint standard applies to future two-handed equipment; only A1 is implemented here.

The two-sheet profile validates all 28 poses and 224 directional body/shadow cells. Back-stowed axes receive the full opaque-body intersection audit, including gloves (the carried-axe grip exception is disabled). All pass. Installation verifies all 67 custom sheet hashes and preserves 65 other sheets and the executable. Its receipt is stored separately as two_hand_back_stow_revision, preserving the existing one-handed town/sword metadata. Private archive: I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Two Hand Back Stow 2026-10-26. Native clip, fitted axe, backups, final sheets, transforms and reviews stay outside Git.

## 2026-10-26 — light warrior bow B1

The next equipment family is WLB: AS, AW, AT, HT, ST, WL, FM, LM and QM. B1 is the available twoHandBow_base01.glb. Death continues to share the approved unarmed sheet; bows have no blocking sheet. This is an asset update for the existing 0.4.1-pre executable, without engine changes.

The Paladin animation collection has no bow clips. Selected Rogue bow idle/walk and rogM_bow_attk_heartSeeker clips are transferred onto the existing Paladin skeleton. retarget_world_motion.py corrects anatomical link directions and preserves the source weapon socket axes, retaining target geometry, skin bindings, textures and materials. prepare_bow_sets.py combines these poses with the approved short-stride walking body and hit reaction. The shot uses native source contact frame 7 at game action frame 11 of 16; recovery blends back to bow idle. Right-hand positioning is corrected toward the string draw plane. These are authored adjustments, not an unchanged native attack.

bake_bow_equipment.py preserves the wooden bow geometry and materials, replaces its original string vertices with an authored string, and adds an authored nocked arrow. Merged glTF morph animation keeps the carried bow upright, flexes its tips and draws the string to the right hand. The decorative arrow disappears after the release pose; the game supplies the actual projectile. check_bow_draw.py verifies grip, nock, string contact and visible/hidden arrow state over all sixteen attack poses. No projectile logic or renderer changes are required.

Town ST/WL use relaxed free hands and the approved final-frame-49 palM_2HM_event_sheathe back-stow reference, accounting for the bow's different origin. Back-stowed equipment is audited against the full opaque body, including hands. Held-bow grip contact is allowed only for the flagged bow equipment. All six motion profiles pass body-contact and full-shadow bounds checks. Spell sheets reuse the three approved WLS spell sheets exactly; the original NN8 bow casts also show no bow.

The nine-sheet pack covers 1,008 directional cells. install_bow_sets.py verifies the starting manifest, stock WLB hashes, render fingerprints, pose audits, draw checks and executable hash before replacement. It preserves all 67 existing custom sheets, bringing the installed total to 76, and retains rollback copies. Private archive: I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Bow B1 2026-10-26. Models, clips, renders and previews remain outside Git. In-game appearance still requires gameplay review; offline bounds and attachment checks do not replace that review.

## 2026-10-27 — bow town carry follows vanilla

The user superseded bow back-stow: keep the bow in hand like vanilla, reserving the back for a future quiver. Original NN8 WLB ST in all eight directions shows a low left-hand grip with the bow's long axis running front to back, approximately horizontal. This exception applies to bows; the approved axe back-stow and other weapons remain unchanged. No quiver has been supplied or added.

prepare_town_bow.py uses the approved relaxed town body and short-stride town walk, closes the left fingers, and moves the hand 10 cm outward and 2 cm forward for clearance. The town mode of bake_bow_equipment.py keeps the bow's major axis horizontal front to back, with its curved belly below its tips. Equipment follows the left-hand grip throughout both animations. The original bow scale, model art, character scale, anchors, southeast lighting and shadow treatment are retained.

Only WLBST (20 poses) and WLBWL (8 poses) are replaced: 224 directional cells. Both profiles pass full body-clearance and shadow-bound checks, allowing intended glove grip contact. install_town_bow.py verifies the complete starting manifest, sheet/layout hashes, render fingerprints and both audits, then archives exact backups and installs with rollback. It preserves the other 74 custom sheets, all combat/casting animations and the executable; total custom sheets remains 76. The separate town_bow_revision receipt supersedes the historical back-stow description in bow_sets. Private archive: I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Bow Hand Carry 2026-10-27. Proprietary artwork and previews remain outside Git. Gameplay review remains necessary.

## 2026-10-27 — T1 light warrior staff

The user selected T1, twoHandStaff_base01.glb, after comparing it with twoHandSorcStaff_base01.glb. The selected staff is fitted at 0.8 of its original equipment scale (about 1.97 m long); character scale, artwork calibration, foot anchors, southeast lighting and approved spell effects are unchanged. Nine WLT sheets are supplied: AS 10, AW 8, AT 16, HT 6, ST 20, WL 8 and FM/LM/QM 20 each, totaling 1,024 directional cells. Death remains shared with unarmed and there is no staff blocking sheet.

prepare_staff_sets.py reuses the approved Paladin two-handed idle, short-stride walk and hit bodies. AT uses palM_2HM_attk_basic, with source contact frame 12 mapped to game frame 11. Its sampled source frames are 0, 1.2, 2.4, 2.4, 4.8, 6, 7.2, 8.4, 9.6, 10.8, 12, 16, 40, 52, 64 and 84. One wind-up pose is held for an additional frame. Arms receive authored forward grip-clearance adjustments of 20–50 cm through the wind-up and swing; target skin bindings, bone lengths and the native body lunge remain intact. This is a fitted animation, not an unchanged native attack.

bake_staff_equipment.py preserves the source mesh and materials, baking rigid staff poses as morph targets in hand.R coordinates. The shaft follows the line between both palms, retains the native axial roll reference and lets the main hand slide along it while the support hand stays near local Y 1.29. This prevents the long butt from entering the torso. These are offline render assets; the game still consumes PNG sheets through the existing renderer.

Unlike bow and axe casts, original NN8 WLT casts retain the staff. The approved Gizmo Operate body and effects are rendered with a closed, steady right-hand staff grip while the left arm casts. Town ST/WL follow the approved two-handed back-stow standard using the native sheathe endpoint, normalized for this model and turned head-up about its shaft midpoint. The bow's low hand carry and reserved quiver space are preserved.

All nine stored-pose profiles pass opaque-body and full-shadow bound checks. Intended glove grip contact is allowed only on explicitly flagged held staff equipment; town back-stow includes gloves in its audit. check_staff_grips.py measures nearest shaft vertices to both palms at the stored game frames. Right-hand distances are below 4.9 cm, including shaft thickness and mesh sampling; both-hand combat/support distances are below 3.5 cm on the left. The left hand is intentionally free during casting. Continuous morph interpolation is not a gameplay requirement because these poses are rendered to discrete PNG cells.

install_staff_sets.py guards the complete starting manifest, stock WLT hashes, fingerprints, all nine pose audits and grip checks, plus the existing 128 MiB decoded image entry limit. The largest retained decoded staff sheet is approximately 70.04 MiB. Installation preserves the previous 76 custom sheets and executable and brings the total to 85, completing the light-armored warrior equipment families. Exact backups, final sheets, models, recipes and reviews are private under I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Staff T1 2026-10-27. No proprietary artwork is stored in Git. The existing executable remains 0.4.1-pre; gameplay appearance still needs an in-game review.

## 2026-10-27 — warning-only PNG memory policy, 0.4.2-pre

The user requested log flags rather than PNG size rejection. The existing executable is now 0.4.2-pre, SHA256 3AAF8B303218301060D6B5A1B5C02BC3406DE0CE8D99342565BC9A0C6D38D5C1. Its PNG loader accepts sheets beyond the old 128 MiB retained, 256 MiB compressed and 65536-pixel dimension caps, subject to format/grid validity, representable sizes and actual allocation success. The sprite cache targets 4 GiB of system RAM and the Windows process-private-commit warning target is 8 GiB; these are not VRAM allocations or a hard game-memory cap. Individual oversize sheets are admitted after LRU eviction. The staff installer likewise reports large-sheet memory warnings instead of asserting the old cap.

Warnings append to hd-sprite-loader.log beside the game configuration and enter the regular application log. Cumulative flags 1/3/7 mean 75%/90%/100% of the relevant target. Logs include the sheet path, dimensions, compressed/retained memory, cache/process usage and action=continue. Transient decoder staging peaks are sampled on Windows. Large canvas clipping uses 64-bit intermediates. The SDL3 application log severity labels were corrected. Environment settings and tests are documented in docs/HD_SPRITE_SHEETS.md and docs/releases/0.4.2-pre.md.

All four renderer/provider tests and the PNG/compositor integration test pass, including real oversized fixtures and dedicated-log checks. The final 4,853-frame HD replay completed with the same reference-save result (57.61 s, 84.2 fps), with deliberately low private test thresholds proving warnings do not prevent rendering. Installation backed up the previous executable as D:/Games/Diablo/Diablo Reincarnated.before-0.4.2.exe and verified preservation of all 85 custom sheets/layouts, existing settings and saves. Both local master manifests now record version 0.4.2-pre and a separate renderer_revision receipt; historical asset receipts remain unchanged. No graphics were rerendered or replaced for this executable update.

## 2026-10-27 — restore motion previously reduced for sheet bounds

The user requested the full versions of sheets whose motion had been changed to fit old limits. Installed-hash provenance identified 22 affected sheets: WLUAS; WLD/WLU/WLH AW; WLD/WLU/WLH BL; WLD/WLU/WLH/WLS/WLM HT; WLD/WLU/WLH FM, LM and QM; and WLNDT. The source PNGs already retained their 8x density. These were primarily fixed-canvas pose compromises, not files downsampled to meet the former 128 MiB budget. Existing native sword attacks already had full motion and padding and are preserved. The approved shortened gait, body scale/brightness, equipment models and unrelated grip/collision fixes remain intact.

audit_canvas_motion.py traces current sheet hashes through render plans and model recipe chains. prepare_full_motion_restoration.py recursively removes old arm_gain, motion_gain, wrist_gain, branch_gains, arm_tuck and weapon_envelope fitting controls from the affected models, while preserving approved overlays, sampling, fingers and stride. It restores the unmodified native faint source without per-direction fall steering or horizontal travel pinning. All eight facings use the same native fall rotated by the original direction order. Grounding remains a shared vertical render placement correction.

The old block recipe overlaid only the shield arm onto an idle body and also held the wrist through its finger helper. Full native blocks now sample the entire palM_1hsSH_attk_withstand body at source frames 6 and 14, keeping native wrists while retaining closed grip fingers. full_motion_block_mount.py converts the approved corrected H3 grip from idle forearm-relative space into hand-relative space, so the shield follows that native wrist. No shoulder/elbow/body attenuation or mesh scaling is used to resolve head contact. Direct source-channel comparison in audit_restored_native_bones.py verifies the three block sheets and death body/wrist channels within 1e-5, excluding only approved closed finger poses.

fit_motion_canvases.py fits transparent output padding and raw capture space to every body/full southeast shadow pose at unchanged camera pixel density and world-ground registration. preflight_equipped_sets.py now delegates to this fitter instead of trying weaker poses. Geometry contact remains a reported failure requiring attachment review; it is never hidden through automatic pose reductions. audit_full_motion_contacts.py reports no checked equipment/body contacts in the final sixteen canonical jobs, with the existing combat-shield forearm-strap/grip contact convention retained.

Six identical shield-casting sheets are aliases of three canonical spell renders. The complete 22-sheet pack contains 2,160 directional cells; sixteen canonical jobs render 1,200 body/shadow cells. All final RGBA bounds, full blurred shadows, direction/frame grids, source fingerprints and layout anchors validate. Before/after death, block and hit GIFs were reviewed at matching world scale. install_full_motion_restoration.py archives exact previous game/mirror PNGs and layouts, verifies the full starting manifest and native audits, and installs only the listed targets with rollback.

Installation completed under I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Unrestricted Motion 2026-10-27/Installed. Models, recipes and raw renders remain in the adjacent private Work folder. All 63 other custom sheets are hash-preserved, including the bow hand carry, staff set, selected sword/mace/axe attacks, town stow and the other unarmed actions. Total installed custom sheets remains 85. The executable stays 0.4.2-pre, SHA256 3AAF8B303218301060D6B5A1B5C02BC3406DE0CE8D99342565BC9A0C6D38D5C1. The manifest records a separate full_motion_restoration receipt. No graphics or proprietary pose data are committed to Git. New in-game feel still needs gameplay review.

### Selected Sorcerer staff melee revision (2026-10-27)

The user selected the Sorcerer candidate over the Necromancer staff melee. Only WLTAT is replaced; all other 84 custom sheets, including the shorter town walking stride, remain unchanged. This is an asset revision for the existing 0.4.2-pre executable, not a new build.

`prepare_staff_attack_revision.py` extracts `sorM_STF_attk_weaponAttack` from local `sorm_all_anims.glb`, retargets the named rest-pose deltas onto the approved Paladin, and samples source frames 0, 0.9, 1.8, 2.7, 3.6, 4.5, 5.4, 6.3, 7.2, 8.1, 9, 12, 18, 27, 36 and 45. The full source time range is represented; the thrust at source frame 9 maps to game impact frame 11. No idle overlay, hand IK, arm attenuation or body-pose substitution is used. The native-channel audit compares 2,352 sampled channel values with maximum error 0.0 after the proportion-preserving retarget.

`bake_staff_native_attack.py` follows the native weapon socket, rather than steering this one-handed attack between both palms. The left hand retains its native free-hand movement. The T1 staff stays at scale 0.8; mesh-local grip (0, 0.4, 0) registers to right-palm (0.0425, 0.0825, -0.002). A fixed five-degree staff-only tilt around the staff's local X axis clears the Paladin head. The previous two-hand mounting method intersected the torso during transition/recovery; it was rejected. The final mount has zero detected staff/body contacts over all stored frames, excluding the intended glove grip surface. The nearest staff vertex remains within 2.5 cm of the right palm; left-hand shaft distance is informational for this free-hand action.

Full-motion bounds fitting produces a 150 by 133 logical canvas at density 8, with the original model scale and ground registration. Raw captures remain 2048 square with the full southeast-light shadow. The sheet is 9600 by 17024 pixels, contains all 128 directional cells, and uses a separate layout anchor. No memory cap, stride adjustment or motion reduction is used to fit this sheet.

The local work is `warrior-3d/staff-sorcerer-final`; the private installation archive is `I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Sorcerer Staff Attack 2026-10-27`. `install_staff_attack_revision.py` requires matching source fingerprints, complete native-body/grip/contact/bounds reports, all 128 rendered body and shadow bounds, the fresh master manifest, and hashes of all existing custom sheets. It backs up the exact game and mirror PNG/layouts separately, updates only WLTAT, verifies the other 84 sheet hashes/layouts and the executable, and rolls back on failure. Proprietary source animation, models, sheets and review media stay local; only authoring tools and this record belong in Git.

### Original Sorcerer grip refinement preview (2026-10-27)

The user rejected the installed native-socket staff orientation because it changed the action shown in the selected Sorcerer preview. The original preview uses the two-palm staff alignment from `bake_staff_equipment.py` and evenly sampled source frames 0, 3, ... 45; these are the requested motion and timing for this refinement. Do not silently substitute the one-handed native-socket mount or retime this review candidate.

At the user's request, `prepare_staff_grip_preview.py` moves both hands forward by a requested 15 cm using the existing two-bone arm solve, carries the staff with the palms, and slides T1 by 15 cm through the grips to reduce the head's forward projection. The T1 head lies toward negative mesh Y: the correct `grip_slide` is -0.1875 at scale 0.8. The first trial used the opposite slide sign and was discarded. The existing baker gains an optional mesh-local `grip_slide=0` argument; all earlier callers retain their original result.

The refined model changes only upperArm, forearm and hand channels on each side. The body-channel audit confirms the other 2,256 channel samples are unchanged, and the original 16-frame timing and model/staff scale are retained. The final staff mesh has zero detected intersections against the torso, head, legs, boots and armor over all 16 stored poses; intended glove contact is excluded. Nearest mesh-vertex grip errors stay below 4.4 cm at the right palm and 2.4 cm at the left palm, including shaft thickness and vertex spacing. The same southeast light and shadow grading are retained.

This is a preview, not a game installation. The previously installed native-socket revision remains in the game until a replacement is installed. Private work: `warrior-3d/staff-sorcerer-grip-refinement`; comparison: `sorcerer-grip-before-after.gif`, original above and adjusted below. Source art, pose data and renders stay outside Git.


The user then requested another 15 cm through the same grip: the current preview is 30 cm total (`grip_slide=-0.375` at scale 0.8). Hands and body are byte-identical to the preceding 15 cm clearance candidate; only the rigid staff placement changes. The public preview preparer accepts an optional total slide in centimetres. Private work: `warrior-3d/staff-sorcerer-grip-30cm`. The 16-pose mesh contact audit remains clear, with nearest-vertex grip distances below 3.6 cm right and 2.4 cm left. This remains a preview; the game installation is unchanged.


The user approved the existing staff rotation and requested a closed left-hand grip after inspecting the close-up. The original two-handed idle supplies only the left finger channels, using `finger_grip=["L"]` and `preserve_grip_wrist_motion=True`. No wrist or attachment transform changes. The finger-only audit finds 15 changed left finger joints and zero error in 8,496 non-finger channel samples. The exact existing 30 cm staff GLB is reused. Private preview: `warrior-3d/staff-sorcerer-left-grip`, with tracked left-hand close-ups in south, west and northwest. This remains a preview; no game sheets were replaced.


The user found that the closed fist still intersected the shaft off-centre. `fit_staff_closed_grip.py` now aligns the actual closed left-hand opening to the exact existing shaft rather than the old palm attachment point. The fitted local grip centre is (-0.04, 0.065, 0) metres with opening axis local Z. Per-frame minimum wrist rotation aligns that axis with the existing line between the original palms; the left arm solve places the opening on that line. The existing rigid staff GLB and all other body/finger channels are unchanged. The generic author accepts optional `hand_grip_poses` world-space position/quaternion targets. A native 30-fps basis check validates Blender/glTF conversions before authoring.

The 16-pose audit reports maximum centre error 0.000000608 metres, maximum axis error 0.0203 degrees, and zero channel error outside upperArm.L, forearm.L and hand.L. Body/armor contact checks remain clear, excluding the intended glove grip. Private candidate: `warrior-3d/staff-sorcerer-centred-grip`; updated close-up: `left-hand-closeup/left-hand-staff.gif`. These measurements register an authored grip opening and do not claim skin collision perfection. The candidate remains a preview, with game installation unchanged.


The user requested the same closure/centring fix for the right hand. The existing two-hand idle supplies only right finger channels first; `fit_staff_right_grip.py` then aligns right grip centre (0.04, 0.065, 0), axis local Z, to the exact existing shaft. The already corrected left hand remains unchanged. At near-full extension, the right grip slides along the shaft by at most 4.41 cm to stay within natural two-bone reach (98.5 percent), rather than offsetting the fist from the shaft or stretching the arm.

Because the staff is parented to hand.R, `rebase_staff_attachment.py` compensates its local morph positions after this wrist correction, preserving the entire previous world-space staff path. The 16-pose audit finds maximum perpendicular grip-centre error 0.000000606 metres, axis error 0.026 degrees, staff-vertex error 0.000000282 metres, zero left-grip movement, and zero animation-channel changes outside upperArm.R, forearm.R and hand.R after right-finger closure. Body/armor contacts remain clear, excluding intended glove contact. The original timing, 30 cm staff slide, scale and left fingers remain unchanged. Private work: `warrior-3d/staff-sorcerer-both-grips`; current right close-up: `right-hand-closeup/right-hand-staff.gif`. Preview only; no game sheet replaced.


The user correctly identified an excessive wrist correction in the right-grip preview. Its rig-relative wrist rotation peaked at 130.7 degrees from the bind relationship. That candidate is superseded by `fit_staff_natural_right_grip.py`: the solver uses a constant shaft-axis sign, moves the elbow, turns the forearm, and allows grip sliding along the unchanged shaft. It searches elbow poles and shaft positions with a wrist-rotation cost, retaining the original torso/legs, left grip, staff path and timing. The author supports optional elbow-pole targets and forearm axial turn within `hand_grip_poses`; existing recipes retain their old behavior.

The revised 16-pose rig audit measures a maximum wrist-relative-bind rotation of 9.66 degrees, versus 130.7 degrees previously. This is a rig diagnostic, not a medical range-of-motion claim. Added forearm turn ranges from +6.73 to -70.12 degrees; elbow movement reaches 20.42 cm and the right grip slides up to 22.5 cm along the staff during the thrust. These are deliberate right-arm changes to avoid forcing the wrist while keeping the approved staff path. Grip-centre and staff-axis alignment remain within 0.000000531 metres and 0.025 degrees, staff world vertices within 0.000000282 metres, left-grip movement zero, and all non-right-arm channels unchanged after finger closure. Body/armor contact checks remain clear. Private preview: `warrior-3d/staff-sorcerer-natural-right/right-hand-closeup/right-hand-staff.gif`. No game sheets installed.


### Town staff carry corrected to vanilla (2026-10-27)

The user identified that the staff must remain in hand in town. Inspection of vanilla NN8 WLTST/WLTWL confirms an upright left-hand carry, not the back stow used for other two-handed equipment. `prepare_town_staff.py` replaces only those two sheets: left fingers grip the upright T1 staff, the elbow/forearm support a near-neutral wrist, and the walking staff leans gently by up to 8 degrees. The exact existing town stand body and approved short-stride walk remain the donors; all non-left-arm channels are unchanged. The right/free arm is retained. Staff scale stays 0.8, the lower end remains 5 cm above the local floor, and southeast light/shadows, density 8, grading and model scale are retained.

`audit_town_staff.py` verifies all 28 poses: maximum nearest shaft-vertex grip distance 3.06 cm, shaft/grip-axis error below 0.014 degrees, wrist rotation below 3.38 degrees relative to the bind relationship, and zero changes to torso, legs, right arm and gait channels. These are rig measurements. Both body/armor contact audits are clear, excluding intended glove grip. Full rendered bounds checks pass for all 224 directional body and shadow cells. WLTST is 7808 by 15360 pixels, layout D1R_SHEET_V1 8 61 96; WLTWL is 7552 by 6144, layout D1R_SHEET_V1 8 59 96. Canvases are fitted to motion and full shadow, without pose attenuation.

Installed with `install_town_staff.py` under the private archive I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Town Staff Hand Carry 2026-10-27, including separate exact game/mirror backups. The master and mirror manifests record town_staff_revision. All 83 other custom PNG/layout pairs and the existing 0.4.2-pre executable (SHA256 3AAF8B303218301060D6B5A1B5C02BC3406DE0CE8D99342565BC9A0C6D38D5C1) are preserved; total custom sheets remains 85. The approved natural-right-arm staff attack is still a separate, uninstalled preview. Private work and installed town previews: warrior-3d/staff-town-hand/work. No proprietary art is committed to Git.


### Approved staff attack installed, hit aligned to frame 11 (2026-10-27)

The user explicitly selected alignment to Diablo damage frame 11 rather than the exact preview timing. `align_approved_staff_hit.py` retimes the approved natural-right-arm, two-centred-grip Sorcerer attack using approved pose indices 0, 0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1, 2.4, 2.7, 3, 4, 6, 9, 12, 15. Approved thrust pose 4 is therefore game frame 11. Pose order, complete start/end motion range, original geometry/materials/skin bindings, closed grips, 30 cm staff position and natural wrist/elbow work are retained. This intentionally lengthens anticipation and compresses recovery within the existing 16-frame game attack; no engine damage timing, animation frame count or executable changes.

The staff uses rigid transforms fitted to approved poses, quaternion interpolation and grip-centred registration, avoiding length changes from direct morph blending during retiming. Exact approved key poses retain staff world vertices within 0.00000184 metres; the frame-11 body pose has zero channel error against approved thrust pose 4. Maximum right wrist rotation remains 9.66 degrees relative to the rig bind relationship; maximum intermediate grip-axis deviation is 4.1 degrees, nearest staff-vertex distance below 4.35 cm. Body/armor contact checks remain clear. `audit_aligned_staff.py` binds these results to the derived model/equipment hashes. All 128 rendered directional body and full southeast-shadow cells pass bounds checks.

`install_approved_staff_attack.py` installed only WLTAT, backing up exact game/mirror sheets and manifests. Current file: 10752 by 16384 pixels, D1R_SHEET_V1 8 84 128, SHA256 F100859468C9AAE30D03C37C0D33CBCF3CF4DB8DB53875C32242272120A00563. Archive: I:/Diablo Sprites/3D Assests/Paladin Candidate 1 Edited/Light Warrior Approved Staff Attack Frame11 2026-10-27. Derived and approved source models, checks and review media remain private; approved originals are copied under Inputs/Approved. Current work: warrior-3d/staff-approved-hit11. The manifests now record staff_attack_revision with timing_choice aligned_hit, visual_thrust_frame 11 and engine_impact_frame 11. The prior preview-only staff-attack status is superseded.

All 84 other custom PNG/layout pairs are preserved, including the newly corrected in-hand town staff carry, approved short-stride walk, other equipment and effects. Total custom sheets remains 85. Executable remains 0.4.2-pre, SHA256 3AAF8B303218301060D6B5A1B5C02BC3406DE0CE8D99342565BC9A0C6D38D5C1. Render/geometry checks are complete; gameplay feel still benefits from an in-game review. No proprietary models, sheets or animation data belong in Git.
