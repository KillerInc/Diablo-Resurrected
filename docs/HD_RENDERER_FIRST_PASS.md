# F10 HD renderer: first integrated pass

The classic DevilutionX software renderer stays the default. F10 switches to a transitional GPU overlay mode with a small green bar in the upper-left corner as a visible indicator. Gameplay state is unchanged. Repeated key-down events are ignored. F10 is no longer the default Quick Message 2 shortcut, but the action remains configurable.

## Image overrides

These PNG files are **optional**. If absent, the original graphics render as before:

- `hd/players/<class>/<direction>_<frame>.png`: animated player frame, with zero-based DevilutionX frame numbers.
- `hd/players/<class>.png`: static class image fallback.
- `hd/monsters/<monster-type>/<direction>_<frame>.png`: animated monster frame, or `hd/monsters/<monster-type>.png` for static fallback.
- `hd/tiles/<dungeon-type>/<piece-id>.png`: optional dungeon tile replacement.

Numbers in file paths are the current DevilutionX enum/piece IDs. Assets are relative to the game's working directory.

The source PNG dimensions are independent of the game's world dimensions. By default an HD image is drawn at the classic artwork's logical size. Each PNG can have an optional `.layout` sidecar with four whitespace-separated floats: `width height pivotX pivotY` in logical pixels. Example: `128 256 64 256` means a 128x256 world-space image bottom-centred on its original tile or actor's ground contact.

The first pass uses existing SDL2/SDL3 + SDL_image. It does not yet offer a dedicated shader/atlas renderer or smooth independent zoom levels; its placement follows DevilutionX's current 1x/2x zoom. SDL1 retains the classic display.

**Known limitation:** this is an opt-in HD compositor over the old framebuffer, not yet a completely independent isometric renderer. HD pieces and characters can overlap classic objects incorrectly. LOS-aware foreground cutouts, lighting/shader parity, GPU compression, 4x atlases, tile ordering, and animation-specific variants remain subsequent work. Suppressing the classic player sprite is only done when an HD replacement is loaded; otherwise the old sprite remains visible.

No Blizzard artwork is committed to this project.

## Scene ordering milestone

The HD compositor now records sprite and tile draw commands per world frame and sorts by screen-space ground-contact Y. At a shared ground depth, terrain draws before actors; otherwise draw submission order stays stable. This corrects overlap **among HD replacements** but does not yet interleave HD draws with non-HD classic artwork.

The GPU pass now uses the same 2x source-to-destination mapping as DevilutionX's original Zoom() (including the left side panel offset), and clips the output to the world viewport so it does not cover the classic bottom/side UI. The F10 toggle also unloads cached replacements, allowing an asset to be updated while in Classic mode.

The command sort, 2x zoom offset and stable tie ordering have standalone C++ regression tests. We still need a unified GPU scene that includes classic and HD graphics to solve *mixed-asset occlusion* correctly.

## Hands-on F10 smoke test without finished HD artwork

From the game working directory, run:

```bash
python3 tools/generate_hd_test_pack.py --out .
```

This creates `hd/players/0.png`, a **synthetic**, high-resolution (384x512) Warrior stand-in. The script does not extract or distribute Blizzard artwork. Start the game with your legally obtained Diablo data, select a Warrior, then press F10. HD mode has a small green marker and displays the deliberately bright placeholder where the original Warrior animation would appear. Press F10 again to return to the original art. This test checks texture loading, anchoring, and switching, **not** animation/lighting parity. Use a fresh working directory or remove the placeholder before adding your own art.

No in-game rendering has been visually verified in CI yet: the automated Linux check builds the engine, while the separate tests validate command sorting, logical dimensions and zoom mapping.
