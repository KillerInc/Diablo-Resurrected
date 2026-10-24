# Stage 3: original-named sprite sheets

The existing SDL3 renderer now resolves installed `hd/plrgfx`, `hd/monsters`, and `hd/missiles` PNG sheets using the original CL2/CEL asset selected by the game. It keeps the existing simulation, GPU presenter, world traversal, UI and Classic mode. There is no new engine and no asset repacking requirement.

## Selection and alignment

The runtime loader annotates each in-memory CLX frame with its original asset path, direction and frame. The annotation is copied with sprite storage, including shared monster animations and cloned/translated sprites. It does not alter the game data archives or save format. This avoids guessing an animation from a mode, or using a class/direction/frame key that conflates actions and equipment.

Player town/dungeon animations, equipment, armor and class graphics therefore follow the same selection as Classic. Monster animation files, type translations, unique-monster draw translations, corpses and missile direction files keep their original identities. The common CLX world draw functions replace only the RGBA world contribution, leaving the indexed game buffer intact. Existing visibility decisions, walking offsets, draw order, masks, classic foreground coverage and UI remain authoritative.

The sheet grid comes from the original file's direction lists and maximum frame count. Column = original direction list, row = original frame. Integer PNG scale is measured against the original sprite width. Cells may be rectangular. Frames draw at their original width with the cell bottom aligned to the classic baseline. Transparent top padding is retained instead of stretching the image to a variable-height frame.

Loose numeric PNG/DDS overrides remain available as the existing fallback when there is no usable named sheet. If no replacement can draw, Classic rasterization still supplies that sprite. Named sheets retain the original direction/frame grid; version 0.4.1 adds an optional named-sheet canvas sidecar described below.

## Expanded HD canvases and fixed anchors (0.4.1-pre)

An original-named PNG may have a UTF-8/ASCII sidecar at `NAME.png.layout`:

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
and bottom alignment. PNG and sidecar resolve from the same asset provider;
malformed metadata or out-of-range anchors preserve the Classic fallback.

Density is explicitly 1, 2, 4, 8 or 16, independent of canvas dimensions. Source
dimensions, streaming decode, retained 2x density and cache limits still apply.
Only the drawing canvas grows; neither the sprite nor game tiles are enlarged.
The Paladin test art uses one fixed camera-projected ground origin for every
direction and action, with the previously approved uniform art scale preserved.
Southeast sunlight casts full moving shadows northwest.

## Color and memory

Sheet colors pass through the sprite's accumulated palette translation, the draw's TRN or per-pixel lightmap, and the current display palette. Truecolor smoothing residuals around the nearest palette color are retained. This follows the vanilla color-control path; it is not an assertion of exact color equality for every interpolated pixel or every artist-authored palette. Alpha and the existing 50% sprite blend are composited in traversal order.

PNG decoding streams one row at a time, avoiding full 8x-atlas allocations. The installed files stay at their original resolution. The current world compositor supports vanilla 1x/2x world mapping and retains up to 2x sampled sheet density for that output. It does not yet render an independently zoomable 8x GPU world. SDL_GPU continues to upload and present the composed image; sprite composition and the sheet cache use system RAM, not VRAM.

The LRU sheet cache defaults to 1 GiB. `D1R_SHEET_CACHE_MB` can set 128–4096 MiB. Individual retained sheets are capped at 128 MiB, source dimensions at 65536 per axis, and compressed bytes at the existing provider limit. Invalid dimensions, unsupported/interlaced PNGs and decode failures fall back rather than being used as sheets. The palette-matching cache is bounded too. F10 clears loaded sheets with the other HD assets.

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
