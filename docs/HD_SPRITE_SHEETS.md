# Stage 3: original-named sprite sheets

The existing SDL3 renderer now resolves installed `hd/plrgfx`, `hd/monsters`, and `hd/missiles` PNG sheets using the original CL2/CEL asset selected by the game. It keeps the existing simulation, GPU presenter, world traversal, UI and Classic mode. There is no new engine and no asset repacking requirement.

## Selection and alignment

The runtime loader annotates each in-memory CLX frame with its original asset path, direction and frame. The annotation is copied with sprite storage, including shared monster animations and cloned/translated sprites. It does not alter the game data archives or save format. This avoids guessing an animation from a mode, or using a class/direction/frame key that conflates actions and equipment.

Player town/dungeon animations, equipment, armor and class graphics therefore follow the same selection as Classic. Monster animation files, type translations, unique-monster draw translations, corpses and missile direction files keep their original identities. The common CLX world draw functions replace only the RGBA world contribution, leaving the indexed game buffer intact. Existing visibility decisions, walking offsets, draw order, masks, classic foreground coverage and UI remain authoritative.

The sheet grid comes from the original file's direction lists and maximum frame count. Column = original direction list, row = original frame. Integer PNG scale is measured against the original sprite width. Cells may be rectangular. Frames draw at their original width with the cell bottom aligned to the classic baseline. Transparent top padding is retained instead of stretching the image to a variable-height frame.

Loose numeric PNG/DDS overrides remain available as the existing fallback when there is no usable named sheet. If no replacement can draw, Classic rasterization still supplies that sprite. Named sheets retain the original direction/frame grid; version 0.4.1 adds canvas metadata and version 0.4.3 consolidates it in the CSV described below.

## Consolidated layout table (0.4.3-pre)

The only runtime layout source is `HD/layouts.csv`. Paths are relative to `HD`,
use forward slashes, and are matched without ASCII case sensitivity:

```csv
path,layout
plrgfx/warrior/wln/wlnst.png,D1R_SHEET_V1 8 48 96
```

The `layout` field contains the same version, density and anchors as the former
individual files. It also accepts the existing four-number layout for numeric
image overrides. Normal CSV quoting, UTF-8/BOM and CRLF/LF are supported.
Duplicate paths, unsafe paths or malformed CSV invalidate the table. Missing
or invalid metadata uses the existing default alignment/Classic fallback;
individual `.layout` files are never consulted.

Each asset provider loads its table on first use and keeps every row in memory
until the process exits. F10 and image-cache eviction do not remove or reload
it. Restart the game after editing the CSV. An image only uses metadata from its
own provider, so an overriding image cannot inherit a lower pack's anchors.

`python tools/hd_layouts.py INPUT_HD OUTPUT_CSV` collects offline render sidecars
into the table without modifying artwork. Runtime installation uses just the
CSV; private render outputs and backups may retain per-image metadata. New
sprite installs must update this table, using `read_table`/`write_table` in that
module. The current warrior installer does so atomically and backs up the old
CSV for rollback.

## Expanded HD canvases and fixed anchors (0.4.1-pre)

An original-named PNG uses the following value in its CSV `layout` field:

```text
D1R_SHEET_V1 8 96 160
```

Fields are source pixel density, horizontal center anchor and vertical baseline
anchor, all anchors in original logical pixels. PNG dimensions still divide by
the original direction/frame grid, but the cell width is independent of the
Classic sprite width. The example uses 192 x 192 logical cells at 8x density.
Its cell center anchor is x=96; the Classic bottom baseline is y=160, leaving
32 extra logical pixels below the baseline. The tile's ground center is 16
pixels above that baseline. The sample's world ground origin is therefore
authored at (96,144), not at its changing visible-body bounding-box center.

At draw time, the expanded cell's anchor aligns to the Classic canvas center
and bottom baseline. Original movement offsets, animation frames, damage/range,
world traversal, palette/light handling and the indexed buffer are unchanged.
The full larger rectangle participates in world rendering and the existing
foreground/UI/viewport clipping. Sheets without metadata keep their prior width
and bottom alignment. PNG and CSV row resolve from the same asset provider;
malformed metadata or out-of-range anchors preserve the Classic fallback.

Density is explicitly 1, 2, 4, 8 or 16, independent of canvas dimensions. Source
format rules, streaming decode and retained 2x density still apply. Version
0.4.2 replaces arbitrary PNG size caps with diagnostics described below.
Only the drawing canvas grows; neither the sprite nor game tiles are enlarged.
The Paladin test art uses one fixed camera-projected ground origin for every
direction and action, with the previously approved uniform art scale preserved.
Southeast sunlight casts full moving shadows northwest.

The user's current local Paladin selection restores the original NN8 canvas
sizes: idle/walk use 96-pixel logical cells with anchors (48,96); the selected
refined punch uses 128-pixel cells with anchors (64,128). All full moving shadows
fit those cells. Larger canvases remain an optional renderer capability, not a
requirement to use the current art. Model scale and fixed ground registration
are independent of transparent canvas padding.

## Player-class preload (0.4.4-pre)

Loading a save or new game preloads every installed named PNG for the selected
local character's sprite class: all armor tiers, equipment sets, town/dungeon
actions and directions. Original CL2/CLX data supplies each grid and width;
unknown/malformed assets are logged and retain Classic fallback. Source PNGs
and `layouts.csv` are not converted or rewritten. The current Warrior set is
255 sheets and 4,794,935,808 bytes (4.47 GiB) of retained 2x RGBA.

MPQ/provenance discovery stays serial. Up to four PNG decoders work during the
loading screen, with synchronized metadata and cache insertion. The loading
bar allocates its first half to game loading and second half to hero sprites.
No gameplay, animation timing, palette/light/TRN rules or save format changes.

The selected class is pinned against the renderer LRU for the game session.
F10, display resets and level transitions retain those entries. Returning to
the menu releases them; a different class replaces previous pinned entries.
Other classes (including remote multiplayer players), monsters and other scene
sprites still load on demand. They use remaining ordinary cache headroom, with
a minimum 512 MiB evictable scene target if the pinned class exceeds the 4 GiB
ordinary target. These are RAM buffers, not VRAM textures or OS-locked pages.
Existing warning-only targets still apply; pinning does not impose a PNG cap.

PNG edits for pinned player sheets require re-entering the game session;
CSV edits still require restarting the process. Headless and SDL1/SDL2 runs do
not preload. Archive providers must expose optional asset enumeration to
participate; current loose HD folders do so with normal provider precedence.

## Color and memory

Sheet colors pass through the sprite's accumulated palette translation, the draw's TRN or per-pixel lightmap, and the current display palette. Truecolor smoothing residuals around the nearest palette color are retained. This follows the vanilla color-control path; it is not an assertion of exact color equality for every interpolated pixel or every artist-authored palette. Alpha and the existing 50% sprite blend are composited in traversal order.

PNG decoding streams one row at a time, avoiding full 8x-atlas allocations. The installed files stay at their original resolution. The current world compositor supports vanilla 1x/2x world mapping and retains up to 2x sampled sheet density for that output. It does not yet render an independently zoomable 8x GPU world. SDL_GPU continues to upload and present the composed image; sprite composition and the sheet cache use system RAM, not VRAM.

As of 0.4.2-pre, PNGs are no longer rejected at 128 MiB retained, 256 MiB compressed or 65536 source pixels per axis. The PNG format's own dimension range, representable allocation sizes, available memory and valid direction/frame grids still apply. Unsupported/interlaced PNGs and decode failures retain the Classic fallback. The palette-matching cache remains bounded. F10 clears loaded sheets with the other HD assets.

The LRU cache defaults to a **4 GiB target**, with an **8 GiB process warning target**. These are system-memory targets, not VRAM allocations or a hard game-memory cap. LRU eviction removes older sheets when space is needed. A single sheet larger than the target is still admitted after other cached sheets are evicted.

| Environment setting | Default | Meaning |
| --- | --- | --- |
| `D1R_SHEET_CACHE_MB` | 4096 | LRU cache target in MiB; positive representable values accepted |
| `D1R_SHEET_WARN_MB` | 128 | Per-sheet retained-memory warning threshold; never rejects a sheet |
| `D1R_PROCESS_WARN_MB` | 8192 | Windows process-private-commit warning target |
| `D1R_SHEET_LOG` | config directory + `hd-sprite-loader.log` | Append-only dedicated warning log |

Warnings also enter the normal application log. `HD_PNG_WARNING` includes source path, PNG dimensions, compressed/retained memory and flags for crossing the former dimension/compressed-size caps. `HD_MEMORY_WARNING` identifies cache pressure, Windows process private commit, and transient decode pressure while staging and retained buffers coexist. Windows private commit includes committed pageable memory; it is not a VRAM or working-set measurement. Process checks occur during sheet loading, not as a continuous whole-game monitor.

Memory flags are cumulative: **1 = at least 75%**, **3 = at least 90%**, **7 = at least 100%** of the specified target. Cache/process high-water warnings are deduplicated until HD assets reset; individual PNG/decode-peak warnings are associated with each load. Each diagnostic records `action=continue`. Malformed files, integer overflow and genuine allocation failures remain errors. The SDL3 application log now labels TRACE/INFO/WARN/ERROR/CRITICAL correctly.

## Full-motion sheet authoring

The equipment preflight now expands transparent canvases and raw capture space
around the authored motion and its full shadow. It never searches for smaller
arm/body excursions to make a fixed cell fit. Capture enlargement preserves
camera pixels per metre, character scale and the layout's world-ground anchor.
Physical contact is reported for review instead of hidden through attenuation.

The 27 October restoration replaces 22 light-warrior sheets whose earlier
recipes reduced movement or redirected a fall to fit old cells. It keeps the
approved walking stride, equipment choices and unrelated fitting corrections.
The death fall uses its native path; full blocks retain native body/wrist poses
and the approved shield grip converted to hand-relative attachment. Bounds,
contacts, source-bone comparisons and previous-file preservation are recorded
by the local restoration pipeline. Artwork and private reports remain outside
Git; see `tools/warrior3d/PALADIN.md` for the source workflow and sheet inventory.

## Validation on 23 October 2026

- All 1,102 installed original-named PNGs have matching extracted CL2/CEL originals; all direction/frame grids divide exactly, and none is interlaced. This is a structural audit, not a visual pass through every animation.
- The earlier unarmed/axe Warrior town idle sheets each matched all 160 original frame silhouettes exactly at original-resolution thresholded alpha.
- `reincarnated_sheet_test` passed provenance/cloning, accumulated translation, streamed PNG decoding/truncation and bad-grid rejection, 2x anchoring, color mapping, original indexed-buffer preservation, per-pixel lighting, half blending and classic foreground occlusion. Build that explicit target in the SDL3 build and run its executable.
- The final game executable passed the full 4,853-frame gameplay replay with HD enabled. The reference-save comparison reported **Same outcome as initial run**. It exercised player equipment/actions, monster movement/combat/death and missiles across levels 1 and 2.
- The final 2,700-frame UI replay passed Classic/HD/Classic switching, Escape menu/cursor, inventory, character panel and zoom. All three zoomed HUD samples matched Classic restoration through the existing capture checker.
- GPU readback images were inspected for actual sheet rendering, foreground overlap and menus. They are GPU texture captures, not desktop screenshots or physical-input verification.
- The final gameplay run took 59.28 seconds (81.9 fps average), including GPU readback/PNG capture overhead, on this machine. The original 256 MiB cache trial took 184.15 seconds (26.4 fps); cache eviction/redecode was corrected before delivery. These are replay averages, not a minimum-framerate guarantee.

The initial sheet-enabled executable SHA-256 was `BB89F8EFD5A61E69F838A78A1CA3E8705F0A83F7B4B59CAC9EABE2EF1861BB2E`. The explicitly versioned **0.4.0-pre** build is `F43F53A3F57090EA4C8B52E5B205C298FEFC01C44BD2C9F38932D3FF13659E8B`; it repeated the full gameplay check with the same reference-save outcome in 57.88 seconds (83.8 fps). Windows file/product versions match the display version. See [0.4.0-pre](releases/0.4.0-pre.md).

Unverified breadth includes a complete playthrough, every class/action/monster skin and spell, multiplayer, physical input, fullscreen/DPI changes and exact color parity for every palette transformation. Missing terrain, object or towner sheets retain vanilla graphics. The installed set has no new floor/wall sheet directory; this change does not invent terrain assets.

## Performance monitoring

Since 0.4.5-pre, press F11 for frame-time, CPU-stage, RAM and sprite-cache metrics.
A once-per-second CSV is recorded alongside the game configuration. See
[performance monitoring](PERFORMANCE.md) for metric definitions and log location.

## Native GPU Warrior pack (0.4.6-pre)

Compiled .gpus/.bc7 resources take precedence for the Warrior on Direct3D 12.
They retain 4x texels in VRAM and render at physical viewport resolution; they do
not pass through the legacy 2x CPU PNG decoder. Original PNGs/CSV stay available
for compatibility. Re-encode compiled resources when changing source artwork.
See [GPU architecture](GPU_SPRITE_PLAN.md) for provider, anchor and cache rules.
