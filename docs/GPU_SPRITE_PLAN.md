# GPU player sprite renderer (0.4.7-pre)

The existing SDL3/Direct3D 12 engine now draws compiled Warrior sprite pages on
the GPU. This is an incremental renderer migration inside the modified executable,
not a replacement engine. Terrain, monsters, other loose HD resources and the
original indexed gameplay buffer retain their existing CPU paths. Other classes
can use compatible PNG rendering when no compiled pack is installed. The virtual
gamepad path currently retains CPU sprite composition to preserve its overlay.

## Asset and loading path

All 255 installed Warrior sheets have compiled 4x-density resources: four times
vanilla width/height and sixteen times the pixel area. Frames are cropped, given
four-texel gutters, and packed into 2048-wide BC7 pages. The selected class is
preloaded and retained in VRAM across equipment swaps, F10, level changes and
normal display resizing. Leaving the game releases its pages. GPU-unavailable or
missing-pack cases retain the existing PNG compatibility path.

The runtime reads `.gpus` frame/page records and `.bc7` block data without
expanding whole player sheets into RGBA RAM. GPU pages and their anchor entries
resolve from one asset provider; all referenced pages stay bound to that provider.
`HD/layouts.csv` remains the single logical anchor source, cached per provider
until process exit. Compiled records contain crop/texture coordinates and density,
not an independent replacement for that anchor table. The original PNGs and
existing CSV entries remain intact, including the original PNG density values.

A reusable upload pool replaces per-page/per-frame staging allocations. Copies
are synchronized with fences during preload and cycled correctly for live draws.
Pooled control textures carry small lighting/coverage maps and palette tables.
The CPU retains no decoded player RGBA atlas when all selected-class GPU sheets
are available. Driver memory and other scene resources are additional costs.

## Drawing and compatibility

Sprites are drawn at physical viewport resolution from their logical game
positions. Lighting, baked/runtime colour translation, fades and alpha follow the
existing palette-based rules in shaders, preserving the truecolour residual.
A shared 64 MiB GPU buffer maps all 24-bit RGB colours to their exact nearest
logical palette entry. It is generated on the GPU and warmed while loading rather
than searched for every sprite pixel or built on the first F10 frame.

Later CPU raster writes transform each earlier GPU actor's colour by `m*S+b`.
Applying the same affine transformation to the base and ordered actors preserves
source-over foreground transparency; opaque coverage masks actors completely.
The original traversal order is retained. UI, menu and cursor coverage participate;
cursor-only restores restore actor coverage too. Synthetic readback tests cover
multiple overlapping actors, transparent and opaque foreground, lighting/TRN,
cursor restoration, resource release and a physical viewport twice logical size.

F10 still selects Classic/HD. F11 adds GPU sheet count, allocated BC7 page payload
and cumulative draw counters. CSV metrics include `gpu_sheets`,
`gpu_texture_bytes`, `gpu_page_uploads` and `gpu_draw_calls`. These are allocation
and activity counters, not measured GPU execution time or driver-reported total
VRAM residency. Process-private commit is not physical working set; do not add
that number to texture payload and call it total physical RAM.

## Offline tools and verification

`prepare_sprite_scale.py` creates frame-isolated lower-density custom PNGs from
approved sources, preserving logical anchors and frame counts. `pack_gpu_sprites.py`
uses the offline ISPC BC7 encoder and validated native grid records; custom art is
Lanczos-resampled to 4x, and the original NN8 pixel-art sheets use nearest sampling.
The encoder is a temporary build tool, not a game runtime dependency. Proprietary
sources, textures, captures and saves stay outside Git.

`validate_gpu_pack.py` checks every page decode, grid, crop, source identity and
anchor table and samples compression error across all 85 custom actions. The
compiled pack must be regenerated when its source artwork changes; dropping a
new PNG does not replace a compiled BC7 resource. `build_gpu_shaders.py` rebuilds
owned HLSL into the checked-in DXBC headers using the Windows SDK.

`run_gpu_replay.ps1` runs isolated tests with a 0.5 mixer master gain. The
`D1R_TEST_AUDIO_GAIN=0.5` override never rewrites normal volume preferences.
`install_gpu_renderer.py` installs only validated compiled resources and the
executable, backs up previous state, preserves all source PNGs/CSV and rolls back
on failure. Replay proof must include actual GPU draws, complete class residency,
no warm page uploads, reference-save equality, UI/F10/F11, and native GPU tests.

## Consolidated metadata (0.4.7-pre)

`HD/sprites.gpus` replaces all per-sheet runtime `.gpus` files. The provider
reads it once, including missing/invalid results, and keeps its lookup table
until process exit. F10, equipment changes and image-cache resets do not reload
it. Sparse overlay indexes fall through by sheet ID; the selected index record,
BC7 pages and CSV anchors always use the same provider. Individual `.gpus`
files are not queried by the renderer. CPU PNG fallback remains available.

The UTF-8 text format (LF or CRLF) is:

```
D1R_GPU_INDEX_V1
DEFAULTS 4 8 96 96
SHEET plrgfx/warrior/wln/wlnst.png 20 3 * * * *
```

The four defaults are density, direction count, logical cell width and height.
A sheet supplies its PNG-relative path, frame count, page count, then those same
four fields; `*` inherits the corresponding default. Explicit values preserve
padded cells and other exceptions. The next page-count lines are filename,
width, height; then direction-count times frame-count lines contain page, x, y,
width, height, crop-x, crop-y, unchanged from the V1 per-sheet metadata. Page
names resolve relative to the sheet's directory. Anchors exist only in
`layouts.csv`. Duplicate IDs, unsafe paths and malformed/truncated records are
rejected. No image payload is stored in the index.

After all encoding workers complete, run `python tools/gpu_index.py PACK/HD`
(or use the packer's `--finalize-index` on a serial run). Private authoring packs
may retain per-sheet intermediates for resuming encodes; validated runtime
file lists contain only the root index and BC7 pages. Validation expands every
index record and compares it with the original metadata, frame proofs and page
hashes without re-encoding. The installer skips identical pages, backs up and
removes loose per-sheet metadata, and restores it if installation fails.

This reduces runtime metadata file opens and centralizes repeated settings.
It does not reduce texture allocation or fix unrelated world-rendering hitches.

### 0.4.7 validation

The consolidated index expands exactly to all 255 original sheet records. All
760 BC7 pages (2,525,855,744 texture bytes), 255 source PNG hashes and the
85-row anchor table match. All six foundation checks and six installer tests
pass, including metadata retirement and rollback. The real GPU synthetic test
passes lighting, transparency, ordering, cursor restoration and native output.
Two 4,853-frame reference gameplay replays produce the same saved outcome; a
normal-speed UI replay covers F10/F11 and both renderer modes. Every replay
loads the 255-record index once, retains all class sheets, and uploads no warm
player pages. Initial class preload measured 4.736 seconds in the first replay;
this is a metadata-management change, not a claim of a frame-rate improvement.
