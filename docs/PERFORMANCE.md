# In-game performance monitoring (0.4.5-pre)

Press **F11** during a game to show/hide the monitor. F10 still switches HD/Classic.
The monitor starts hidden; logging runs during active gameplay in either mode.

The display updates once per second:

- FPS and average, 95th percentile and maximum frame interval in milliseconds.
- CPU-side wall time drawing the world, composing the HD frame and presenting it.
- Counts of intervals above 33.33 ms and 50 ms.
- Windows process-private RAM, decoded sheet-buffer RAM, sheet count and pinned-player count.
- Sheet-cache hits, misses, successful decodes, failures/missing-file fallbacks and LRU evictions during the last reporting interval.

Frame intervals include frame limiting and display synchronization. Presentation time
includes CPU waiting for the display/GPU; it is **not GPU execution time**. Drawing
covers DrawView; composition covers ComposeHdFrame. These stages do not include every
other part of the game loop. RAM is private committed process memory, not working set
or VRAM. Sheet bytes are retained CPU pixel buffers, not compressed PNG file sizes.

`performance.csv` is written beside the game configuration. On this Windows build the
default is `%APPDATA%/KillerInc/Diablo Reincarnated/performance.csv`. `--config-dir`
changes that directory. `D1R_PERF_LOG` can select an explicit file path.
Each process appends a session comment, CSV header and one row per reporting interval.
Cache counters and decode/read elapsed milliseconds in each row are interval deltas;
resident counts/bytes are snapshots. Decode elapsed sums worker wall times, so parallel
work can overlap. Missing/rejected optional replacements retain Classic fallback and
can appear in the failure counter. LRU evictions exclude explicit level/display/class
resets. Logs contain metrics only, not art or save contents.

Loading screens and time spent inactive are excluded. Switching render modes resets
the reporting window. Preload duration/count/bytes remain in the existing
`HD_PLAYER_PRELOAD` application-log entry. Menus over an active game remain measured.
A partial final interval is not emitted. Percentiles use fixed storage for the latest
4096 intervals in the reporting window; average/max/hitch counts cover every interval.
Logging flushes once per reporting interval; disk logging and optional overlay text
have a small cost. Capture-enabled/timedemo runs are diagnostic validation, not
representative normal-play benchmarks. No frame cap, memory cap, source image size,
anchor, animation, gameplay or cache residency policy is changed by the monitor.

Validation uses synthetic percentile/hitch tests, real compositor/CSV checks including
loading/inactivity exclusion, F11/F10 replays, unchanged reference saves and selected
class residency checks. User saves/preferences and installed artwork are preserved.

## GPU sprite metrics since 0.4.6-pre

F11 also displays GPU-resident sheet count, allocated BC7 page payload and cumulative
draw calls. CSV adds gpu_sheets, gpu_texture_bytes, gpu_page_uploads and gpu_draw_calls.
Page bytes exclude the shared 64 MiB RGB lookup, render targets/control buffers and
driver overhead; they are not a measurement of total resident VRAM. CPU sheet bytes
exclude these GPU pages. A zero class-preload byte count now means no CPU RGBA player
atlas, not an unloaded class; the resident sheet count and GPU counters prove loading.
Cache hit/miss/decode counters describe the CPU PNG cache. GPU uploads/draws are
cumulative process counters. Different app sessions may append a new CSV header.
Test scripts also sample physical working set separately from private commit.
