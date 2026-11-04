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
