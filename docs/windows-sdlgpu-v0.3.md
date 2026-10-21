# Windows x64 v0.3 phases 1–4

Branch: `feature/windows-x64-sdlgpu-v0.3`, based on PR #7 head
`7f48b71ef2b6de896a5db48464530f30a58796a8`. PR #8 targets the v0.2
development branch. Neither earlier baseline is merged or rewritten.

## Presentation ownership

The SDL3 window is created without an SDL_Renderer. One SDL_GPU device claims
the window and presents both Classic and HD via upload, GPU blit, and swapchain
submission. F10 changes composition, not the window, device, simulation, or
save state. The presenter handles minimized swapchains, transfer/texture
cycling, resizing, aspect ratio, integer scaling, and matching mouse-coordinate
conversion. SDL1/SDL2 retain their existing presentation backends.

This is explicitly a **CPU truecolor compositor with SDL_GPU presentation**,
not a shader-based world rasterizer or SDL_Renderer overlay. No external shader
compiler or runtime shader assets are needed for the GPU blit path.

## Independent world and UI

The HD world starts as an empty RGBA canvas. Original raster operations emit
their lit opaque/blended spans into that canvas as scrollrt executes them.
Loose HD replacements are composited at their original traversal slots. Their
Classic sprites still render into the indexed buffer, but their spans alone
are suppressed in the HD canvas. Every missing replacement therefore falls
back individually, without switching the whole frame or menu to Classic.

The completed Classic world framebuffer is never the HD background. The
indexed buffer remains intact for Classic rendering and game/cursor logic.
After DrawGame finishes, subsequent raster writes populate a transparent UI
canvas in output coordinates. Menus, inventory, character panels, HUD and
cursor are composited above the HD world. Persistent HUD/panel regions are
preserved from indexed UI drawing. Supplemental comparison captures raw UI
writers; actual raster coverage handles equal-color occluding writes.

## Diablo depth semantics

There is no global screen-Y or role sort. DrawFloor, DrawTileContent,
DrawDungeon, and DrawOOB retain their traversal, moving-actor source-tile
corrections, pre/post objects and missiles, lighting, microtile masks, special
arches and delayed town tree foliage. The same ordered spans that cover a
Classic actor cover the HD actor, including identical palette-color writes.
Transparent foreground spans blend against the HD destination.

Tile test replacements currently occupy the floor phase; Classic wall
microtiles and foreground masks continue in their original slots. This avoids
replacing a multistage wall with one incorrectly ordered whole-cell billboard.

## Loose test assets

Executable-adjacent, installed, preference and working-directory providers keep
their existing precedence and same-provider `.layout` sidecars. Player and
monster lookup tries direction/frame PNG, direction/frame DDS, static PNG,
then static DDS. Missing or invalid images fall back to the individual Classic
sprite. The synthetic Warrior remains a temporary test image.

DDS decoding supports 32-bit masked RGB(A), BC1/DXT1, BC2/DXT3, and BC3/DXT5.
Unsupported DDS formats, cubemaps, volumes, invalid masks, oversized and
truncated files are rejected. BC7 and the `.anim` builder are not implemented.
Replacement art has no new material/normal-map lighting system in this phase.

## Validation tools

The four Release foundation tests cover switching/layout, retained submission
order/zoom, provider fallback, and DDS decoding/rejection. Generate isolated
UI coverage with `tools/create_sdl3_validation_demo.py --out <folder> --extended`.
It adds inventory, character panel and zoom to the Classic/HD/Escape sequence.
`--gameplay-hd` also prepares demo 0 with F10 after its tenth existing game
tick, preserving the upstream gameplay and reference-save comparison.

For optional GPU-texture inspection, set `D1R_FRAME_DUMP` to an existing output
directory before launch. Every 100th gameplay presentation (starting at 50)
downloads the composed texture through an SDL_GPU transfer buffer, waits for
its GPU fence, and writes a PNG. Normal gameplay performs no readbacks or file
writes. These images validate GPU texture contents; they are not OS window
captures and do not independently prove desktop scaling or physical input.

The executable remains `Diablo Reincarnated.exe`, with matching
`d1reincarnated.mpq` and isolated KillerInc preferences/saves. Original game
data is local validation input only and must not enter source or packages.
Publication is gated on the exact tested CI artifact and its file hashes.
