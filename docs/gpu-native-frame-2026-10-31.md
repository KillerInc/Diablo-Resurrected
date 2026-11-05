# GPU native frame, 0.4.12-pre

Supported terrain no longer paints the native indexed tile pixels each frame.
The native decoder builds reusable opaque row runs once; scene traversal queues
those runs, original palette indices and lighting levels. The GPU resolves
palette lighting alongside BC7 terrain and ordered wall blends. Unsupported
light tables and missing materials retain native drawing.

The presenter uploads the indexed frame directly and resolves palette colours
on the GPU, avoiding the full-frame CPU RGBA conversion and HD canvas. Zoom,
affine UI composition and foreground actor coverage retain their prior order.
Classic and virtual-gamepad paths retain their CPU canvas. Native screenshots
temporarily restore indexed terrain painting. Loading screens reset frame state.
Odd-width uploads/readbacks use aligned transfer rows.

BC7 page uploads now have a separate transfer pool. Actor masks, lighting and
palettes are batched into one per-frame transfer instead of repeatedly cycling
a page-sized transfer allocation for small controls.

## Validation

Synthetic GPU readback passes cover lighting, ordered translucent walls, UI,
zoom 1/2, missing materials, native screenshots, virtual-gamepad fallback,
193-pixel row pitches and Classic/HD transitions. Existing sprite readback,
provider and saved-mode checks pass. All 1,107 compiled sheets (2,779 pages,
8,937,177,088 bytes across the entire pack) upload without PNG input; residency
is bounded. Two copied reference saves retain identical outcomes. Separate
UI/capture replays exercise F10/F11 and menus. Matched scene captures retain
wall and sprite appearance; version/FPS text and cursor regions are excluded.

Sequential capture-free runs at 1920x1080, zoom and per-pixel lighting enabled,
measured 87.51 / 86.12 FPS on installed 0.4.11 and 115.80 / 115.54 FPS on 0.4.12.
The first loading/warmup interval is excluded. This is about a 33% gain in this
scene, not a universal performance guarantee. Peak process private memory was
4,415,320,064 / 4,424,151,040 bytes versus 3,724,533,760 / 3,724,398,592 bytes.
Private memory is process commitment, not VRAM. Selected-class texture residency
remains 3,069,730,816 bytes in this scene; warm intervals add no page uploads.
CPU stage timings remain wall timings rather than GPU execution measurements.

Simulation, scene traversal, lighting-map construction, UI rasterization and
visibility/coverage work still involve the CPU. This is not a complete GPU-only
renderer. D1R_GPU_TILE_COMMANDS=0 restores native tile painting;
D1R_GPU_INDEXED_PRESENT=0 restores CPU frame conversion for diagnosis.

All graphics tests use isolated saves/settings, muted sound and the left display.
Installation backs up executables and preserves artwork, layouts and normal
preferences/saves. Only source, synthetic tests and this sanitized report belong
in Git; all user-supplied art and captures remain private.
