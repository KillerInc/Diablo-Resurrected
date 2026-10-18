# F10 HD renderer: first integrated pass

The classic DevilutionX software renderer stays the default. F10 switches to a transitional GPU overlay mode with a small green bar in the upper-left corner as a visible indicator. Gameplay state is unchanged. Repeated key-down events are ignored. F10 is no longer the default Quick Message 2 shortcut, but the action remains configurable.

## Image overrides

These PNG files are **optional**. If absent, the original graphics render as before:

- `hd/players/<class>/<direction>_<frame>.png`: animated player frame, with zero-based DevilutionX frame numbers.
- `hd/players/<class>.png`: static class image fallback.
- `hd/tiles/<dungeon-type>/<piece-id>.png`: optional dungeon tile replacement.

Numbers in file paths are the current DevilutionX enum/piece IDs. Assets are relative to the game's working directory.

The source PNG dimensions are independent of the game's world dimensions. By default an HD image is drawn at the classic artwork's logical size. Each PNG can have an optional `.layout` sidecar with four whitespace-separated floats: `width height pivotX pivotY` in logical pixels. Example: `128 256 64 256` means a 128x256 world-space image bottom-centred on its original tile or actor's ground contact.

The first pass uses existing SDL2/SDL3 + SDL_image. It does not yet offer a dedicated shader/atlas renderer or smooth independent zoom levels; its placement follows DevilutionX's current 1x/2x zoom. SDL1 retains the classic display.

**Known limitation:** this is an opt-in HD compositor over the old framebuffer, not yet a completely independent isometric renderer. HD pieces and characters can overlap classic objects incorrectly. LOS-aware foreground cutouts, lighting/shader parity, GPU compression, 4x atlases, tile ordering, and animation-specific variants remain subsequent work. Suppressing the classic player sprite is only done when an HD replacement is loaded; otherwise the old sprite remains visible.

No Blizzard artwork is committed to this project.
