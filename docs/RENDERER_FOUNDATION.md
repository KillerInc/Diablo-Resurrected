# Diablo-Resurrected dual-renderer foundation

## Current state

At the time of this initial patch, this repository contained only its original README, not DevilutionX. The C++ code added here is a tested, standalone **foundation**, not a working Diablo renderer. F10 must be connected to the upstream game's SDL keyboard dispatch after the engine is imported.

## Engine bootstrap

Work on a dedicated integration branch from a clean checkout; run:

    bash scripts/import_devilutionx.sh

The script merges DevilutionX's master history (preserving both project histories). Review all changes, keep upstream license notices, and run the original build and tests. DevilutionX's Sustainable Use License restricts commercial derivatives. Do not add extracted Diablo artwork to Git.

## Rendering contract

- **F10** toggles Classic and HighDefinition only on a fresh keyboard key-down, ignoring key repeats. Classic is the startup default.
- **One shared gameplay simulation:** both renderers consume the same dungeon, actors, animation frames, RNG and line-of-sight state.
- **One world renderer per frame:** do not render two full worlds on top of each other. Keep original UI drawing initially as a separate last pass.
- **Preserve legacy geometry:** do not globally change the hard-coded 64x32 tile dimensions. Adapt grid positions into a new camera's logical projected coordinates.
- **Source texture resolution != world size:** a source sprite 384x512 may render as logical 96x128, and use the same logical bottom-center pivot (48,128) as the original. A 1024x2048 wall might occupy 128x256 logical pixels.
- **Zoom is camera transform:** zoom changes the on-screen footprint, not source dimensions, gameplay positions or collision.
- **Preserve original pivots:** retain player, monster, item, object animation offsets from DevilutionX (getRenderingOffset).
- **Occlusion:** only gameplay-visible actors qualify to fade foreground artwork actually covering them. Do not reveal unseen monsters across LOS-blocking walls.
- **Fullscreen:** world rendering should fill available viewport; panels are overlays.
- **HD backend:** provide GPU sprite compositing, large atlases, compression, and mipmaps; SDL3 GPU is a candidate, not chosen by this patch.

## Identified upstream integration points

- Source/engine/events.cpp and Source/diablo.cpp: F10 input.
- Source/engine/render/scrollrt.cpp: world draw traversal and ordering.
- Source/engine/dx.cpp: CPU backbuffer upload/presentation.
- Source/utils/display.cpp: viewport and window geometry.
- Source/vision.cpp and Source/lighting.cpp: gameplay visibility.
- Source/player.h, monster.h, items.h, objects.h: sprite offsets and positioning.

## Standalone tests

    cmake -S Source/reincarnated -B build/renderer-foundation
    cmake --build build/renderer-foundation
    ctest --test-dir build/renderer-foundation --output-on-failure

Covers mode toggle/key repeat, same placement for original and 4x HD sprites, a massive wall texture with modest logical size, zoom, and invalid metadata. This suite does **not** build the full Diablo engine.

## Next milestone

Integrate the DevilutionX source, connect keyboard event F10 and a dual render dispatcher, then display Warrior, Skeleton and Cathedral tiles using the new GPU renderer. Verify that switching at runtime preserves the game state and all legacy sprite anchors.
