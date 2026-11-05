# GPU terrain renderer â€” 0.4.11-pre

The SDL3/D3D12 renderer now resolves the visible terrain background on the GPU
from the private 4x-dimension BC7 tile atlases. Existing Diablo traversal,
indexed rendering, game logic and scene order remain intact. This is the next
step in the existing executable, rather than a replacement engine.

## Drawing and compatibility

* Re-encoded frame pointers retain their original MPQ frame IDs. Split floor
  foliage uses the original tile origin, including its 16-pixel displacement.
* Native raster spans record tile ownership, actual lit palette indices,
  original indices and lighting levels. Opaque writes clear older translucent
  layers; linked blend records retain the exact order of 50% wall blends.
* The fullscreen GPU pass samples the BC7 tiles, applies palette lighting and
  combines the ordered background with the UI. HD actors retain their existing
  foreground coverage masks and are drawn afterward.
* The old CPU HD RGBA world surface is neither allocated nor painted when GPU
  terrain is active. Classic indexed drawing still runs. UI drawing remains on
  the CPU; its existing retained HUD is reused. The GPU combines the UI with the
  world using background weight plus additive color, preserving transparent UI.
* Tile artwork can differ from native colors: native indices disambiguate
  palette aliases without overwriting the BC7 art's own colors. A synthetic GPU
  readback explicitly tests this, both lighting paths and both zoom modes.
* Pages use the existing process/session cache; F10 and display resets keep
  terrain resources. Loading warms the current level after player preloading.
  Game exit releases terrain references and native-index decode caches.
* Upload data is batched into one copy pass. Transfer/storage allocations grow
  geometrically rather than reallocating for small changes in blend count.

GPU terrain activates automatically when the compiled current-level tile sheet
is available. `D1R_GPU_TERRAIN=0` selects the previous CPU HD background for
comparisons. `D1R_GPU_TERRAIN_NATIVE=1` is a diagnostic control that resolves
native colors through the same GPU composition path. Neither setting changes
saved graphics preferences. Missing/unsupported terrain retains the existing
CPU HD background and Classic fallback behavior. The initial material binding
supports eight BC7 pages per terrain sheet; all five supplied atlases fit (two
or four pages). This is not a PNG dimension restriction.

## Private pack

Only five terrain records are added to the runtime index: town, cathedral,
catacombs, caves and hell. They contain 8,999 original microcells, use 12 BC7
pages and add 155,140,096 compressed texture bytes (147.95 MiB in total).
Only the current level's terrain is loaded, alongside the selected player's
existing class cache. Other character classes are not preloaded.

The combined pack contains 1,107 sheets and 2,779 pages. The actual GPU loader
successfully uploaded every record, one sheet at a time, without PNG input.
`HD/sprites.gpus` stays the sole compiled index; `HD/layouts.csv` stays unchanged.
The remaining prepared CEL/PCX resources are not installed by this terrain
change. Their UI/title-screen integration is separate work.

`tools/install_terrain_pack.py` verifies the staged index, every new page hash,
all previous records and the validation proof. It backs up the old index,
refuses to overwrite unknown art and atomically replaces the index. Renderer
installation separately backs up the executables and updates the private
installation manifests. No art, MPQ data, captures or saves are published.

## Validation

The synthetic terrain GPU readback checks native zoom 1/2, per-pixel and
per-tile lighting, changed artwork colors, repeated ordered wall blends,
opaque/translucent UI and F10 resource retention. Existing GPU-sprite,
HUD/compositor, asset-provider and saved-mode checks also pass. Synthetic
installer checks verify original-record preservation and rejection of unknown
artwork before any metadata change.

Two copied gameplay reference replays preserve their saved outcomes. A muted
UI replay on the left secondary display exercises F10, F11 and menus. Exact
matching gameplay captures are compared separately from performance runs;
exclude the live FPS text and the two independently positioned cursor regions.
The nine final captures have zero RGB differences elsewhere.

At 1920x1080, zoom enabled and per-pixel lighting enabled, repeated capture-free
controls measured 70.19 / 68.50 FPS with the previous CPU HD background and
85.73 / 86.28 FPS with GPU terrain. These are scene-specific, active-gameplay
intervals, excluding the first loading/warmup interval. They are not a promise
of the same gain on every map. The final installed-candidate control measured
70.45 FPS versus 88.09 FPS (25.0% higher). CPU command/present timings are wall timings,
not GPU execution measurements.

The CPU still performs indexed terrain drawing and lighting-map generation.
Direct GPU rasterization of the remaining native scene commands and HD UI
resource rendering remain later steps; this change removes the duplicated HD
background pixel work first.

## Installed build

Release SHA-256: `D3D75FB317512F9A7F5F386C6EFA50602D54AB9B24B295D190FB9E40560746BE`.
Debug SHA-256: `1FDFF49DD08D71654E5B53A43956CCEEA99FD75640C30F7E7878A5C77D7C458D`.
Both are version 0.4.11-pre. The prior binaries and index are backed up locally.
The installed-build isolated UI smoke replay also completes successfully;
normal preferences, saves, authoring sprites and the layout CSV are unchanged.

The replay runner now defaults to full-game saves. Use `-Shareware` explicitly
for spawn/shareware fixtures; forcing shareware for a full-game save otherwise
looks for the wrong archive and produces an “Unable to open archive” error.
