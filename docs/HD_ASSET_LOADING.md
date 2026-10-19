# Diablo Reincarnated HD assets: loose today, archives later

This implementation applies to the **new renderer's optional HD replacements**. DevilutionX's original data and MPQ loading remain unchanged. The renderer requests a virtual asset name such as `hd/players/0.png`; it does not call `IMG_Load(filename)` directly anymore.

## Loose file folders and precedence

All roots contain the `hd/` folder. Paths are checked in this order (first existing, valid asset wins):

1. **Current working directory:** `./hd/...` — convenient during development.
2. **User data directory:** `<DevilutionX PrefPath>/hd/...` — user-installed overrides.
3. **Executable folder:** `<DevilutionX BasePath>/hd/...` — portable installation.
4. **Engine assets directory:** `<DevilutionX AssetsPath>/hd/...` — shipped or unpacked defaults.

There is no manifest, conversion step or repacking requirement: copy PNGs and optional text sidecars to a matching directory. No art is distributed by this repository.

Example:

```text
hd/
  players/
    0.png                       # static Warrior smoke-test art
    0/
      0_0.png                   # class 0, direction 0, frame 0
      0_0.png.layout            # optional logical size/pivot metadata
  monsters/
    12/
      2_3.png
  tiles/
    1/
      123.png
```

Use `python3 tools/generate_hd_test_pack.py --out .` to create a non-Blizzard 384×512 placeholder Warrior. Start the game from that directory and press F10 to compare it against classic art. The graphics still use the old renderer's logical 1×/2× world-space coordinates.

The `.png.layout` files contain four whitespace-separated numbers:
`width height pivot_x pivot_y` in *logical world-rendering pixels*, not source texels. PNGs without sidecars inherit classic draw dimensions and effective bottom-centered pivots.

Asset IDs must be normalized relative paths separated by `/`; absolute paths, `..`, `.`, empty path segments and backslashes are rejected. A single loose resource is limited to 256 MiB of compressed file data. Successfully loaded and missing images are cached until F10 switches modes or the SDL renderer is recreated, so editing files while staying in HD mode does not hot-reload them.

## Future archives: zero renderer changes

`Source/reincarnated/asset_provider.hpp` defines:

- `AssetProvider::read(assetId, bytes)`: one virtual filename to compressed file bytes.
- `LooseFileAssetProvider`: reads those bytes from directories today.
- `AssetStore`: resolves a virtual filename through mounted providers, with controlled precedence.

A future ZIP, MPQ or custom archive implementation only needs to provide `read()`, supplying exactly the same PNG and layout bytes. Mount it with `GetHdAssetStore().mountFallback(...)` to keep all loose overrides **higher priority**. There is no archive reader or encryption/compression format defined or promised in this patch.

Image and sidecar metadata are loaded as a **pair from one provider**. If you override a PNG in a higher-priority loose folder without providing a sidecar, its metadata defaults to the original game size and pivot rather than borrowing the lower-priority pack's `.layout`.

The bytes flow through SDL_image's in-memory image decoder (`IMG_Load_RW` on SDL2 or `IMG_Load_IO` on SDL3), and layout sidecars are read from the same abstraction. Texture-cache invalidation after mounts is still the caller's responsibility; F10 toggling invokes `ResetHdAssets()`.

## Verification

`reincarnated_asset_provider_test` exercises loose reading, multiple roots, precedence, a fake archive backend, missing-file fallthrough, and traversal rejection without SDL. The top-level Linux CI also builds the game to verify the SDL2 integration. SDL3 needs a separate platform build for its image-stream decoder.

This patch does **not** fix classic/HD depth interleaving, gameplay visibility, GPU compression, atlas loading or independent smooth zoom.
