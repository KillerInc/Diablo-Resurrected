# Private MPQ art preparation

The new offline pack covers every CEL/PCX resource in the extracted vanilla
DIABDAT directories `levels`, `ctrlpan`, `data`, `items`, `objects`, `towners`,
`ui_art` and `gendata`. Existing players, monsters and missiles are already
compiled in the installed 1,102-sheet pack and are not rebuilt here.

Scale is **4x width and 4x height: 16x the native pixel count**, matching the
current sprite density. Scaling uses nearest-neighbour sampling and preserves
vanilla artwork; it does not synthesize new artistic detail. BC7 uses the same
`alpha_fast` encoder profile as the current pack.

## Completed assets

| Directory | Prepared resources |
| --- | ---: |
| Terrain and special level overlays | 8 |
| Main HUD/control panel | 9 |
| Other data/UI, legacy fonts and inventory art | 21 |
| Loading/interstitial screens | 10 |
| Items, ground animations and quest maps | 75 |
| Objects, including unused original assets | 70 |
| Town NPCs and their additional animations | 14 |
| PCX title/menu/button/font/portrait atlases | 78 |
| **Total** | **285** |

The five terrain CELs contain **8,999 microcells**, not eight-direction actor
animations. Their original MIN references establish all six shape types with
no conflicts or unreferenced frames. Original frame order, native index values,
alpha, palette banks, MIN/TIL/SOL/AMP layout inputs and PCX font metadata are
preserved privately.

The compiled output contains **294 BC7 pages**, **960,315,392 texture bytes**
(915.83 MiB), and one `HD/sprites.gpus` index. Its 12,690 logical cells include
padding cells and PCX storage blocks; this is not an animation-frame count.

Large PCX images retain their original image layout and source dimensions.
Their GPU storage is divided into 128x128 native-coordinate blocks, with
explicit metadata distinguishing storage blocks from animation frames. Known
engine colour keys are retained; unspecified legacy colour keys are not guessed.
Native index/alpha images remain available for later palette or masking work.

## Reproducible pipeline

1. Build `reincarnated_extract_mpq_art`. Give it the original MPQ, a private
   newline-delimited archive-name list and a **new** output directory. It uses
   the existing game's read-only MPQ reader and rejects absolute/traversal paths.
   The validation run extracted **350 requested graphics/metadata files with
   zero missing entries** from the actual archive, rather than trusting an old
   export directory.
2. Run `tools/prepare_mpq_art.py RAW REPO NEW_PREPARED_DIRECTORY`.
   Engine loader constants/TSVs establish normal CEL widths. The remaining
   assets use CEL header offsets marking 32-row boundaries; every available
   block must establish the same width. This independently agrees with known
   engine widths for 64 assets. No widths remain unresolved.
3. Retain explicit raw palettes, including the JASC-PAL text palette belonging
   to the sword-flip asset. Hell has no `l4.pal`: its prepared base uses the
   actually present `l4_1.pal`, with all variants and native indices preserved.
4. Use `tools/pack_gpu_sprites.py --inventory ... --page-size 4096` with private
   inputs/output. The default remains 2048 for existing pack workflows; larger
   pages accommodate a 640-pixel-wide source frame at 4x without shrinking it.
   Finalize the one index only after all disjoint workers finish.
5. Optional `--solid-blocks` accelerates nearest-neighbour 4x art: each solid
   4x4 block is encoded once per distinct RGBA colour and reused. Synthetic
   tests verify bit-identical output to the full encoder, including alpha and
   cache reuse. Nonuniform blocks retain the normal encoder. Existing model
   artwork and compiled pages are not changed.
6. Build the native reference tools and run `tools/validate_mpq_art.py`.
   `reincarnated_verify_tile_export` renders original tile data through
   `ReencodeDungeonCels` and `RenderTileFrame`. `reincarnated_verify_cel_export`
   uses `CelToClx` and `ClxDraw` for all other CELs. Two sentinel backgrounds
   distinguish transparent pixels from opaque colour-index zero.
7. Run `reincarnated_gpu_pack_upload_test` on the PNG-free compiled pack. Its
   hidden window initializes no audio and holds only one sheet at a time.

The synthetic decoder tests cover CEL/group offsets, row orientation, geometry,
opaque zero, malformed runs, tile alignment padding and CEL-header ambiguity.
Compiled-index tests now include terrain, HUD, data, items, UI and loading-screen
namespaces while retaining path safety and the existing world namespaces.

Legacy UI frame-width references were verified in the original engine source:
[small font and character panel](https://github.com/diasurgical/devilution/blob/master/Source/control.cpp),
[large menu font](https://github.com/diasurgical/devilution/blob/master/Source/gmenu.cpp),
[medium scrolling font](https://github.com/diasurgical/devilution/blob/master/Source/minitext.cpp).

## Validation results

- All **8,999** tile microcells match native-engine index and alpha output
  pixel-for-pixel.
- All **202** other CEL sheets match engine conversion/rendering pixel-for-pixel.
- All **78** PCX atlases retain source index pixels and the specified alpha policy.
- Every BC7 page decodes and every populated frame is compared with its prepared
  source, including page/crop bounds and transparent gutters.
- Maximum per-frame visible RGB RMSE: **0.5773503 / 255**; alpha RMSE: **0**.
- Actual GPU upload passes for **285 sheets / 294 pages / 960,315,392 bytes**,
  without PNG loading and with bounded residency.

## Runtime status and next integration

**This is an asset-preparation milestone, not an installed HD terrain/UI patch.**
The installed 0.4.10-pre executables, authoring PNGs, BC7 pages, layout CSV, saved
mode and user settings/saves remain unchanged. No partial replacement index is
installed. New art stays in the private `D1R_Tiles_UI_BC7_2026-10-31` directory.
Only tools, tests, namespace support and this report belong in Git.

The existing terrain hook only checks full-tile legacy variants and does not
draw the new compiled microcells. Integration must bind original CEL frame IDs
through the engine's re-encoding/remapping and preserve floor/foliage separation,
dynamic level palettes, lighting, doors and foreground transparency/order.
Objects/NPCs already have world-sheet provenance hooks; items and UI need their
own drawing/provenance handling. PCX image blocks must be assembled/cropped in
source coordinates. Cached HUD fragments and fonts also need dedicated support.
All needed art and project source are present; a renderer integration pass is
required before claiming these resources appear in-game.
