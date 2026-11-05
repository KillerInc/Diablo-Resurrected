# Ordered GPU actor batch, 0.4.13-pre

Actor masks and lighting already upload before drawing. All visible actors now
share one render pass, preserving their original draw order and blend state.
Each draw still binds its own BC7 page, coverage, light levels, palette and
uniforms. This reduces pass setup and repeated render-target load/store work;
it does not merge actors or change their geometry.

Per-slot palette textures remain resident and upload only when the full palette
bytes change. Byte comparison handles cycling palettes and mutable monster TRN
values without relying on pointer identity. Mask/light textures still refresh
each frame; resizing those textures does not invalidate an independent palette.
Destroying the GPU device releases both the cached bytes and textures.

D1R_GPU_ACTOR_BATCH=0 restores the earlier per-actor passes and unconditional
palette uploads. D1R_PROFILE_HD records cumulative draw/pass counts, palette
uploads and control transfer bytes. CPU submission timing is not GPU execution
time. The game simulation, terrain traversal and coverage preparation still
involve the CPU.

## Validation

The synthetic GPU readback exercises ordered overlapping actors, translucent
foregrounds, opaque occlusion, lighting and colour translations at native 2x
output. It also checks 300 actor draws over 250 frames use 250 render passes
and only four palette uploads, including invalidation when colours change.

Repeated sequential 1920x1080 capture-free runs measured 118.92 / 115.80 FPS
on installed 0.4.12 and 118.60 / 120.26 FPS with batching. Excluding the first
warmup interval, these results overlap ordinary run variation; do not claim a
reliable FPS improvement from this change. Peak private process memory remains
about 3.72 GB. Selected-class texture residency remains 3,069,730,816 bytes and
warm intervals add no page uploads or CPU player decodes.

The benefit established here is fewer render passes and redundant palette
transfers. Larger gains still require reducing CPU terrain traversal/preparation.

Two copied gameplay references preserve their saved outcomes. Twenty paired
Classic/HD/UI captures match outside the live performance text and the animated
menu-selection markers. These captures are separate from FPS runs. Full-pack
GPU upload, terrain readback and the debug companion are checked before install.
Graphics tests remain muted on the left display with isolated saves/settings;
artwork, layout metadata and normal preferences are preserved.

## Build identities

Release SHA-256: `46EAC70D15DC0B413F419479CB2FD6372D74E90BCF081273A4FE96BC91537D27`.
Debug SHA-256: `021B630A23833788794167265BBE29F792883BBB3C23B11960CA8877382441E6`.
Both report 0.4.13-pre. Previous executable versions are backed up before replacement.
