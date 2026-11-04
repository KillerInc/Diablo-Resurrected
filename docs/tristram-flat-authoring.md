# Layered Tristram canvas and flat-paint export

This replaces the attempted full 3D reconstruction as the immediate texture
authoring route. It assembles the user's original art on the native town grid,
keeps every overlapping fragment independently accessible, and exports pixels
back into their original atlas identities. It does not generate new artwork by
itself or install a replacement pack. All art and derived documents stay private.

## Created private deliverables

`Tristram-layered.ora` is the full 28,672 x 14,336 OpenRaster canvas at density 4.
Its 29,879 fragment layers retain native painter order, grouped by contiguous
draw diagonals. Underlying covered pixels remain in the layers. Shared source
images initially reference the same PNG; all 3,584 atlas slots are also available
as canonical `frames/NNNN.png`, including slots not drawn on this map.

`town-preview.png` is a small whole-town overview; `mergedimage.png` is the full
resolution composite. The latter is streamed in 128-pixel stripes instead of
allocating a 1.5-GiB canvas for each editing layer. `project.json` retains source
hashes, the exact world origin, frame identities and individual layer locations.

The assembled map contains no baked NPCs, UI, actors or game lights. It is the
native base town, not a claim that the terrain has already been remastered.

## Flat painting workflow (preferred)

Use `town_canvas.py region PROJECT REGION --rect LEFT TOP WIDTH HEIGHT`, where
the rectangle is in native projected world pixels. It writes `paint.png`, an
unchanged `reference.png`, and a protected per-pixel source-address map. The
prepared private project includes twelve building-group regions covering all
fourteen buildings. Rectangles match the existing native comparison canvases.

Paint RGB details directly on `paint.png`, at its original dimensions. Preserve
its alpha and placement. Then run:

```
python tools/town3d/town_canvas.py apply-region REGION EDITED.png NEW_PROJECT
python tools/town3d/town_canvas.py export NEW_PROJECT NEW_PROJECT/Tristram-layered.ora EXPORT
```

The importer maps each changed visible pixel to its original fragment and local
pixel, preserving hidden/unmodified pixels. Shared fragment edits propagate to
all their world occurrences and are counted in `paint-report.json`. If a source
pixel receives different colours in two visible places, the import rejects the
edit rather than choosing a last writer. Partial-alpha composites are not
paintable because their colour belongs to more than one source.

Edits requiring genuinely different artwork for the same shared fragment need a
separate reviewed frame/MIN mapping change; this tool does not silently create a
runtime override. That limitation should guide texture edits around repeats.

Use a sibling output project. Never edit the protected reference/address files.
Import rejects stale source frames, resized images and changed alpha. Regions
for a following edit should be created from the latest project, not an older one.

## Direct layer editing (alternative)

Open the ORA in an OpenRaster-capable painting application. Preserve native
layer names, order, opacity, blend modes and positions; edit within layers.
All instances of a shared frame must agree. Export accepts normal editor crops
around transparent borders and restores the original RGB under transparent
texels. Preview-only visibility toggles do not remove source layers on export.

Do not mix direct ORA edits with canonical-frame/region edits in the same project:
export the edited ORA first and create a new project from that resulting atlas.

## Create from original inputs

```
python tools/town3d/town_canvas.py create ATLAS.png town.min native-object-map.json PROJECT
python tools/town3d/town_canvas.py export PROJECT PROJECT/Tristram-layered.ora EXPORT
```

The atlas must be column-major with 128 rows and 32 logical pixels per cell.
At density 4 the town sheet is 3,584 x 16,384. The MIN reader retains the engine's
native block permutation, half-cell offsets and vertical pair ordering.

`tools/town3d/audit_town.py` separately records complete-town 3D comparison
coverage and every fragment/world use; it is useful reference, not a required
component of the flat painting path.

## BC7 validation

Encode the exported sheet with the existing `pack_gpu_sprites.py`, inventory
`levels/towndata/town.png: {columns: 28, rows: 128, source_density: 4}`, 4096-pixel
pages and the existing `alpha_fast` profile. Consolidate the private runtime
index after encoding. Solid-block reuse is optional; detailed painted pixels
automatically use normal BC7 compression. No downsampling is introduced.

The real unmodified project round trip retained every source RGBA pixel. All
four newly encoded BC7 pages matched the installed pages byte-for-byte. The
hidden/silent runtime-loader test uploaded one sheet, four pages, 62,455,808
bytes, with no PNG input. Nothing was installed. This proves the slicing/export
route, not the quality or gameplay validation of future painted artwork.

Eight synthetic checks cover exact round trips, linked edits, shared conflicts,
alpha preservation, editor cropping, layer order, flat-paint re-slicing and
shared-pixel conflicts. Future art changes still need visual seam checks, BC7
quality inspection and in-game occlusion/lighting checks before installation.

## Quest and entrance variants are required

The base canvas alone does not show every native tile. In `Source/levels/town.cpp`,
`DrlgTPass3` selects fountain mega tile 342 at (60,70) while Poisoned Water is
available and unfinished, and mega tile 71 when done or unavailable.
`CleanTownFountain` also switches to tile 71. These are alternate MIN fragments,
not merely a global palette change.

The catacombs entrance uses `FillTile(48,20,320)` while
`IsWarpOpen(DTYPE_CATACOMBS)` is false. The open artwork comes from the unmodified
sector2s DUN tile at (1,10), currently mega tile 321. The original warp logic in
`Source/levels/trigs.cpp` remains authoritative; do not infer state from artwork.

`town_states.py` reads the user's original TIL, sector2s DUN, MIN, object map and
atlas. It exports both reference views and all four native source-cell maps,
which can be passed to `town_canvas.py create` for state-specific canvases.
Its manifest distinguishes shared and state-only source frames. For current
retail inputs:

| Structure | States | State-only source frames |
|---|---|---|
| Fountain | Poisoned / clean | 3542–3547 / 594–597, 602–603 |
| Catacombs | Closed / open | 3298–3303, 3309–3311 / 3312–3320 |

Fountain frames 598–601 and 604–605 are shared. Catacombs frames 3297 and
3304–3308 are shared. Edit the union of both frame sets and keep shared source
pixels consistent; preserve water colour differences and the blocked versus
passable entrance. A base-map-only painting pass is insufficient.

The extractor verifies that its poisoned/closed views exactly match the base
canvas. Three synthetic tests check local 2x2 mega replacement, sector-derived
open tile identity, truncation handling and type-bit-independent frame IDs.
Alternate-state generated artwork remains a preview until registration,
per-state atlas assembly and runtime state-transition validation pass.

## Reused ground texture pass

Ground art must be edited by canonical frame, never independently at a town
location. The first private candidate selects 198 manually reviewed common
grass/dirt/path fragments, used at 5,661 positions on the base town map. It is
a first material pass, not a claim to cover all ground: other floor fragments
can contain building bases, shoreline, rocks or quest-specific illumination.

`pack_ground_art.py PROJECT PAGE_PLAN MIN SOL OUTPUT_NEW_DIRECTORY` checks every
selected frame's uses throughout the original MIN table: all must be in the
bottom pair of non-solid floor pieces. A frame also used higher in architecture
is excluded. Private page plans retain each frame ID and its painted atlas slot.
The painter supplies texture detail; the packing pass restores exact native
alpha and a two-render-pixel outer rim, with a four-pixel feather inside it.
Detail is transferred around the original local colour field, preserving native
grass/path transitions. Matching only a tile's average colour was insufficient:
it left bright interiors surrounded by visibly dark rims. No per-instance art,
frame remapping, MIN changes, collision edits or runtime code changes are used.

All 3,584 atlas slots are checked after reassembly. Unselected RGBA and every
original alpha channel remain exact; protected rims are also exact. Five
synthetic tests cover masked and opaque borders, missing paint, mixed
ground/architecture references, and preservation of a native colour gradient.
The resulting full atlas can use the normal BC7 packer; detailed blocks use the
ordinary encoder instead of solid-colour reuse. Verify metadata identity, decode
quality and real GPU upload, and review joins in assembled town views before
installing. Exact border pixels are a compatibility guarantee, not proof that a
texture's visual scale or repetition is artistically approved.

### Material replacement experiment (not installed)

The detail-transfer candidate above was rejected as insufficiently different
from the original. Preserving original edge RGB is not a user requirement;
native tile reuse, masks and layout are. Do not describe the earlier filter as
an approved ground overhaul.

`replace_ground_materials.py PROJECT PAGE_PLAN MIN SOL DIRT GRASS OUTPUT_NEW`
instead replaces visible ground RGB with new dirt/grass materials. It samples
them through the inverse native isometric projection, using a periodic material
field. Every occurrence of a canonical frame must resolve to the same UV phase;
conflicting phases fail before output. A reflected material sample gives equal
opposing edges. Bilinear sampling includes both axes. The source colour field
locates dirt/grass transitions and retains baked shadows and coloured light,
while replacing the original fine pixel texture. Four synthetic tests cover shared-frame translation,
periodic edges, adjacent half-cell sampling and alpha/hidden-pixel preservation.

The private 214-frame experiment replaces 5,965 occurrences while retaining all
unselected RGBA and all alpha exactly. This demonstrates replacement and reuse,
not finished artwork: fountain/object fragments still contain baked old ground,
and those visible transitions require a separate art pass across both quest
states. Generated assembled-area previews are art direction, not packable atlas
replacements. Keep them labelled and private. No candidate from this experiment
is installed or approved, and the earlier candidate's BC7 upload results do not
validate this new artwork.

## Complete vanilla-town authoring and release path

The final workflow assembles the aged building art, new ground materials and
scenery into the existing 3,584-cell atlas. The source remains 3584x16384 RGBA at
four times native dimensions, with 28 columns, 128 rows and 128px cells. There
are no MIN/TIL/SOL/map edits, additional terrain layers, frame remaps or engine
changes. Hellfire remains outside this art pass.

`assemble_town_art.py PLAN OUTPUT_NEW --dependencies PRIVATE_OPENCV_DIRECTORY`
registers painted RGB to native views and writes through verified source-owner
maps. Native alpha and hidden RGBA remain exact. Shared addresses get one
deterministic sample, preferentially from the most complete visible occurrence.
An explicit initial atlas/coverage permits incremental assembly; reassignment
unlocks samples without erasing previous authoring elsewhere. Optional
`source_cells` masks select one native object occurrence. Never treat unchanged
background scenery in a building preview as authoritative scenery artwork.

`audit_town_art.py PROJECT COVERAGE OUTPUT_NEW --ground-plan GROUND_PLAN`
streams the native painter-order owner canvas and audits visible SOURCE PIXELS,
not just changed-frame counts. The private final base-map audit accounts for
29,124,784 visible source pixels, with zero pending pixels. Constant-black cells
1047/1048 are deliberately retained masks. Coverage proves provenance, not
artistic quality: also inspect assembled close views and the whole town.

`reconcile_town_seams.py PROJECT ATLAS OUTPUT_NEW --dependencies OPENCV_DIRECTORY`
finds canonical fragment joins where original coarse colours agree within six
levels but painted channels jump by at least 18. It balances shared boundary
samples and feathers bounded corrections inside the existing cells. Corrections
are capped at 24 levels per channel per pass; alpha, hidden pixels and native
constant-black masks are preserved. Original sharp material boundaries remain
ineligible. Review the result; this does not guarantee perfect texture or
geometric continuity in generated art.

Author and inspect clean/poisoned water, open/closed catacombs and caves, and the
open Hell fissure plus its closed ground variants. `southern_warp_states` reads
the original sector3 and sector1 DUN files: the closed Hell loop writes overlapping
2x2 blocks at EVERY x from 36 through 45, including x=46 in the adjoining sector.
The four closed floor choices cover the native source-tile alternatives; their
random placement remains game logic. `town_canvas.region(..., layers=...)` can
expose a state or omit occluders for authoring without changing the town map.

Pack the final atlas with the existing BC7 encoder and normal terrain inventory
(`columns=28`, `rows=128`, `source_density=4`, page size 4096). Finalize the private
root index after encoding. The prepared release has four pages, 62,455,808 GPU
bytes (59.56 MiB), exactly the installed page/crop/frame records. Full decode
validation measured RGB MAE 0.468/255, worst-frame MAE 1.292/255, maximum alpha
error one and zero crossings of the 0.8 alpha threshold. The real D3D12 pack
loader uploaded all pages without PNG input or retained CPU player RGBA.

`install_town_art.py GAME_HD PACK_HD AUTHORING_PNG` is inspection-only by default.
After runtime review, `--install --backup NEW_PRIVATE_DIRECTORY` stages and
verifies each of the four town pages and the authoring PNG, then replaces them
with rollback on failure. It requires identical compiled metadata/layouts and
native alpha, and never writes the root index, layout CSV, executable, settings
or saves. Close the game before installation and restart afterward because GPU
textures and metadata are cached for the process lifetime. The executable build
number does not change for an artwork-only release.

Run replay checks from untouched fixtures, not old replay output saves. For a
fresh town capture, the existing offline save tool's `hero-fixture INPUT OUTPUT_NEW`
mode writes a new hero-only test archive, verifies the decoded hero is unchanged
and verifies it has no saved dungeon. The normal executable can then start a
fresh town. Keep fixtures, archives, art, captures and validation manifests
private. Graphics tests remain muted, use copied settings/saves and the left
monitor. SDL's `SDL_WINDOW_ACTIVATE_WHEN_SHOWN=0` and
`SDL_WINDOW_ACTIVATE_WHEN_RAISED=0` avoid taking focus during tests.

### Completed Tristram validation (2026-11-04)

The final vanilla-town pass covers all 29,124,784 visible base-map source pixels
and the unique well/entrance state pixels. Native tile IDs, alpha, hidden RGBA,
map data and collision remain unchanged. Both fresh reference gameplay replays
finished with the same saved-game outcomes as their references. All 38 offline
town-tool tests passed, including interrupted-install rollback. The native
hero-only fixture helper built and verified byte-identical decoded hero data.
A separate fresh-town capture from the normal 0.4.22-pre executable confirmed
GPU terrain loading and the authored buildings, ground and scenery. This was a
visual capture run, not a performance benchmark. The original short capture
attempt reached its timeout; its output is not counted as a completed replay.

The artwork is private. Repository history contains only the authoring tools,
synthetic tests and documentation. Texture joins can still need artistic polish;
coverage and seam reconciliation are not a claim of perfect visual continuity.

Installed the four validated BC7 pages and viewing PNG with verified rollback
backups. Post-install hashes match the tested pack; the executable, root index,
layout CSV and all five normal save/config files are unchanged. The fresh-town
normal-executable replay completed with exit 0. Restart the game to use the new
process-cached terrain textures.


### Foreground and consistency correction pass

The first installed pass missed `levels/towndata/towns.png`. This is the native
foreground tree-leaf sheet, not an optional patch. `InitTownPieces` maps terrain
piece IDs to special frames; `scrollrt` draws them after the following diagonal
so they cover actors. A terrain-only source coverage audit cannot detect stale
foreground artwork or establish visual completeness.

`town_foreground.py` mirrors those placements and delayed draw order for combined
offline views. Terrain microcells and 64x224 special sprites have separate pixel
address ranges. `apply_scene_art.py` gathers one RGB sample per canonical source
pixel, rejects hidden/mixed-alpha edits and preserves both sheets' geometry.
Include foreground trees when reviewing houses, riverbanks and the whole town.
Do not mix a new base tree with an unchanged foreground canopy. Review repeated
occurrences, not just the authoring reference; preserve original special-frame
counts and renderer ordering.

The correction workflow includes the foreground canopies, underlying trunk joins,
cathedral surface consistency in close overlapping views, the detached repeated
rock shard, coarse stumps, and the squared riverbank joins near Adria. A distinct
tree baked into Adria's building tiles also needs its own combined edit.
Native alpha, hidden RGBA and compiled terrain/foreground frame/page metadata
must still match the installed originals exactly. Artwork stays private.

NPC scale comparisons must use actual sprite density and body proportions:
Warrior authoring PNGs can be 8x while their GPU frames are 4x. Normalize to the
compiled density before comparing; do not mistake half of a source cell for a
complete player. Compare seated heads/arms/torsos, not standing bounding-box
height. `rescale_npc_sheet.py` applies one offline transform to all native cells,
including props and baked shadows, around the existing game anchor. It preserves
cell size, order, native frame count and timing. Farnham's correction uses 0.88.

The BC7 packer permits an explicit offline alpha_fast/alpha_basic/alpha_slow
profile, recorded in its proof and checked when resuming. This changes encoding
work only, not runtime texture size or format. Decode every resulting frame.
Farnham's existing AA edges already have BC7 alpha quantization: baseline alpha
RMSE was 1.988/255 with 673 crossings at the outline threshold. The smaller
alpha_slow candidate measured 2.209/255 and 687 crossings, with zero black baked
shadow pixels crossing the threshold. Maximum alpha error alone is not a useful
whole-sheet quality measure; check edge RMS, actual decoded appearance and
shadow exclusion. Terrain/foreground binary masks retain the stricter zero
threshold-crossing check.


Correction release verification: 43 town-tool tests passed. All 3,620 source
frames were decoded and compared; both terrain sheets retained identical native
metadata, maximum alpha error one and zero outline-threshold crossings. Real
D3D12 upload passed for three sheets, six pages and 65,716,224 bytes, without PNG
input. A fresh muted replay using the normal executable and isolated hero/config
finished with exit 0; its capture was visually reviewed. This inactive-window
capture is not an FPS benchmark. The whole-town combined view and eleven close
building views were also reviewed, with extra repairs for the Adria bank corner,
her distinct building tree and repeated stumps.

The paired terrain/foreground pages and viewing PNGs were installed with private
rollback backups. Farnham uses a new content-named BC7 page and a single updated
record in the consolidated index; all other records and the layout CSV are
unchanged. Post-install file hashes match the tested pack. Normal saves,
settings and executable remain unchanged. There is no executable version bump
for these artwork changes. Restart to load the new process-cached textures.

Only the 15 special frames referenced by native InitTownPieces are reauthored;
unused original frames 3/4/5 remain in the 18-frame sheet. Native geometry and
frame numbering are preserved. Fine native silhouette edges and some texture
joins can still benefit from further artistic refinement; this pass does not
claim geometrically seamless generated artwork everywhere.
