# UI coverage transfers, 0.4.16-pre

Unmodified UI coverage is implicit in the shader. Native occupancy, palette
indices and rectangular clipping still determine which pixels appear. This
avoids allocating, copying and uploading a full RGBA coverage image for each
glyph, panel slice and item on every frame. UI draws retain their original order.

A native raster write or inventory palette transformation materializes coverage
only for affected draws. Explicit UI masks retain their uploaded bytes per
control slot; different contents, dimensions, texture growth or a world draw
in that slot invalidate reuse. Palette bytes still refresh independently, so
fades and colour translations do not freeze. Frames with no changed controls
skip the transfer-buffer map and copy pass entirely.

Cursor snapshots distinguish an implicit mask from a newly materialized one.
Restoring a cursor can return a draw to implicit coverage and discard the
temporary hole. Retained HUD components, dialogs and progress scenes can carry
implicit masks without storing full images. World-actor masks and lighting
retain their existing upload path.

`D1R_GPU_UI_CONTROLS=0` materializes and uploads UI masks each frame for comparison.
`D1R_PROFILE_HD` adds cumulative `mask_uploads` and `implicit_ui_draws` alongside
control bytes. Counters describe CPU submissions/transfers, not GPU execution
time or actual VRAM residency. This change reduces control transfers; it does
not combine all UI geometry into one draw or cache a final inventory image.

Synthetic GPU readback covers native/HD artwork, opaque zero, clipping, palette
fades and translations, materialized opaque/blended overlap, restoration from
implicit cursor coverage, retained HUD invalidation and Classic fallback. Both
optimized and comparison controls are checked; an unchanged UI scene must add
zero control-upload bytes after warm-up.

## Loading bar

The game-loading bar previously used a direct SDL surface fill. The HD loading
background covered that CPU-only write. It now uses the same `FillRect` path as
other GPU UI rectangles, above the restored loading background. Classic still
uses indexed pixels. Starting a loading screen also explicitly starts a fresh
UI batch. Synthetic readback checks two increasing widths, and a real loading
replay captured the visible fill increasing to its full 534-pixel extent.
`D1R_TRACE_LOADING` optionally logs the displayed width and active UI path.

## Measured results

A steady inventory profile reduced submitted control bytes from 3,196,928 to
1,019,904 per frame (68.1%), and mask uploads from 168 to 16 (90.5%). The number
of draws remains 168. Private process memory was about 30 MB lower in the paired
tests; this is not an actual VRAM measurement.

Sequential CPU profiles of the final executable versus 0.4.15, using the final
three active intervals, measured UI work at 1.406 versus 1.485 ms/frame, HUD/cursor
at 0.176 versus 0.195 ms/frame, and terrain/sprite command submission at 1.154
versus 1.605 ms/frame. These are CPU wall timings.

Repeated capture-free inventory FPS comparisons varied: old/new were
108.86/104.36, 113.74/120.59 and 104.85/96.87. A world-only pair measured
147.81/155.29. The first two pairs and transfer profiles used the same optimized
GPU code before the loading-only fix; the third inventory pair used the final
executable. These runs demonstrate reduced transfers and CPU submission work,
not a repeatable overall FPS improvement across conditions. CPU world traversal,
raw raster work and UI draw submissions remain costs.

Both reference saves, the debug replay, HD/Classic transitions and frontend
captures passed. The inventory panel matched the previous build pixel-for-pixel
in the reviewed 320x350 comparison region. The graphics pack is unchanged; its
previous PNG-free full-pack upload proof remains applicable, and installation
rechecks every compiled file hash plus authoring PNGs and layouts.
