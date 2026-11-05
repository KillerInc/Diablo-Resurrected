# GPU terrain span resolution, 0.4.14-pre

Previously the CPU expanded cached native tile rows into per-pixel owner,
index/light and transparency-head arrays every frame. The shader sampled those
arrays and traversed a separate blend node for each translucent pixel.

The CPU now records compact ordered spans with original palette indices,
lighting bytes and the BC7 tile owner. Each screen row has 32-pixel bins that
link only the spans intersecting that bin. The GPU walks newest to oldest,
checks coverage, resolves lighting and BC7 colour, and accumulates ordered
50% wall blends until it reaches the last opaque write. It does not need the
CPU-expanded owner/index grids or per-pixel wall nodes. Native fallback raster
writes enter the same stream, including custom-table colours. Actor occlusion
coverage remains on the CPU and retains the previous traversal order.

Original index/light bytes are copied without expanding them to RGBA. Span
records, bin links and byte data use separate byte-addressed GPU buffers.
Aligned transfers preserve odd-width images. Device teardown releases the new
buffers. Existing class/terrain page residency and root metadata caches remain.

D1R_GPU_TERRAIN_SPANS=0 restores the previous pixel-grid path. The earlier
D1R_GPU_TILE_COMMANDS and D1R_GPU_INDEXED_PRESENT comparison switches remain.
D1R_PROFILE_HD reports span/link/byte counts alongside skipped native tile draws.
Simulation, scene traversal, lighting-map construction, UI rasterization and
actor coverage preparation still involve the CPU.

## Validation

Synthetic readbacks cover both lighting modes and zoom levels, BC7 colours,
ordered repeated wall blends, raw/native fallback writes crossing 32-pixel
boundaries, opaque overwrites between translucent layers, UI, Classic toggles,
native screenshots, missing materials, virtual-gamepad fallback and odd-width
resize. The new span path, previous pixel-grid path and native-drawing path
are checked separately. Actor compositing/translation readback also passes.

All 1,107 compiled sheets (2,779 BC7 pages) are checked through the GPU loader
without PNG input. Gameplay tests use copied saves and isolated muted settings
on the left secondary monitor. FPS comparisons exclude loading/warmup and
frame capture. Source/tests and sanitized measurements belong in Git; artwork,
saves, extracted data and captures remain private.

## Performance

Repeated capture-free runs at 1920x1080 with zoom and per-pixel lighting enabled
measured 118.24 / 119.32 FPS on installed 0.4.13 and 147.17 / 146.90 FPS with GPU spans.
The previous pixel-grid path in the new build measured 120.82 FPS. These active
intervals exclude the first loading/warmup interval. Results are scene-specific,
not a promise for every map or GPU. CPU submission timings are wall timings,
not GPU execution measurements.

The profiled scene queues 41,549 spans, 42,071 bin links and 1,505,064 bytes of
index/light data, with zero per-pixel blend nodes. The profiled CPU floor stage
is about 1.02 ms and tile-content stage about 2.16 ms per frame; they still
include traversal, span preparation and actor coverage. Peak private process
memory is 3,688,312,832 / 3,681,488,896 bytes versus 3,722,293,248 /
3,720,986,624 bytes on the controls. This is not a VRAM measurement.

Both gameplay reference outcomes match. Twenty paired UI/Classic/HD captures
match outside live performance text and animated menu-selection markers.
The graphics pack, authoring images and layout table are unchanged.

## Build identities

Release SHA-256: `2FC83B2B6D22A27DDA7BE1CFD7DF779329F7585D486774D5C071369AC4C6A0AD`.
Debug SHA-256: `C8D2F4A7ED735CD886502AB2816A1DD38A7ECC5C6D2F495DD8EFD96CBC1C538B`.
Both report 0.4.14-pre. Previous executables are backed up before replacement.
