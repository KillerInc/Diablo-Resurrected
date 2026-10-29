# GPU sprite migration: measured starting point and first test

29 October 2026. This is a proposed migration, not an installed GPU sprite renderer.
The installed executable remains 0.4.5-pre; F10, F11 and class preloading are unchanged.

The current SDL3 backend uses Direct3D 12 for presentation. `gpu_presenter.cpp`
uploads a CPU-composited frame. `hd_renderer_sdl3.cpp` draws sheet pixels, palette
matching, TRN/light/fade and alpha on the CPU into logical-screen-sized surfaces.
The sheet decoder retains 2x samples. Removing that reduction alone would consume
more RAM without making a logical-resolution render target show all 4x texels.

The intended replacement stays inside the existing modified engine:

1. Convert source art offline to 4x dimensions (16x vanilla pixel area). Crop
   individual frames, pack texture pages with filter-safe padding, and retain
   original logical pivots/direction/frame mappings. Encode BC7 before gameplay.
2. Upload compressed pages to SDL_GPU textures and release CPU staging copies.
   Draw HD sprites at physical window resolution with logical-world coordinates
   mapped to that viewport. Keep nearest-pixel screen scaling as requested.
3. Port existing lighting, TRN/fades and alpha rules to shaders. Preserve Classic
   traversal and foreground masks; never regroup sprites in a way that changes
   overlap. Keep the original low-resolution CPU buffer where gameplay requires it.
4. Move the selected-class resident cache to GPU resources. Keep bounded upload
   staging in RAM; avoid retaining a second, full RGBA class copy. Load/prepare
   resources before gameplay and track fences/lifetimes without per-frame readback.
5. Add actual GPU timestamps and residency/budget measurements to the monitor;
   distinguish measured GPU time, CPU submission/wait, texture allocation estimates
   and driver-reported VRAM usage. Retain Classic fallback and existing save logic.

The first in-game proof should use one Warrior idle and walk page: correct scale
and pivot, town/dungeon lighting and fades, wall occlusion, UI/cursor/menu overlays,
F10 switching, and reference-save replay outcomes. Then expand to the remaining
player actions and classes. Expanding RAM preloading is not this GPU solution.

At identical uncropped pixel counts, the existing 255-sheet Warrior set would be
approximately 17.86 GiB RGBA at 4x or 4.47 GiB BC7 without mipmaps. BC7 estimates
exclude index/mask data, padding, staging and other game resources; packing can
reduce unused area. They are not a guaranteed total VRAM figure.

A private, uninstalled 4x preparation contains all 85 custom Warrior sheets,
verified against installed source hashes. Every source dimension is halved,
logical anchors and frame counts are preserved, and each frame was resized
independently with Lanczos. Its PNGs total 662.62 MiB and RGBA pixels total
7,183,509,504 bytes; none of that proprietary artwork is included in Git.
The source 8x sheets and installed executable are unchanged. The user's config
was separately backed up before changing only Scaling Quality from 2 to 0.
The 4x pack is deliberately not activated with the current hidden 2x decoder.

`tools/prepare_sprite_scale.py` reproduces the private preparation from an HD
folder, install manifest and native-grid records in a validated application log.
Its output must be a new directory. Before installation, validate rendering and
memory residency with the new backend; update layout density to 4 while retaining
logical anchors. Do not install this staged pack and call it a GPU conversion.
