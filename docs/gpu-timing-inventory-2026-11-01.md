# Inventory retention and diagnostic timing, 0.4.17-pre

The existing SDL3 renderer retains the completed inventory in one GPU render
target. Its visual-state key covers the background, panel placement, grid,
visible item cursors/quality/usability/two-handed state and hovered item.
Tooltips and the cursor remain outside the layer. A matching inventory queues
one composite draw rather than rebuilding its item/background commands.

Palette bytes are checked again during presentation, preserving fades that
change after commands were queued. Physical viewport changes rebuild the target.
The target uses the full physical viewport to avoid fractional-scale crop/anchor
rounding; only the inventory region is composited. At 1920x1080 it occupies
8,294,400 GPU bytes. This is a GPU RGBA render target, not decoded CPU player art.
The original compressed sheets and their layout anchors remain unchanged.
Premultiplied composition preserves translucent two-handed weapon previews.
`D1R_GPU_INVENTORY_CACHE=0` selects uncached drawing for comparisons.

## Timing

`D1R_CPU_PROFILE_LOG` retains CPU stage wall timings and adds thread cycle/CPU
accounting counters. Windows `GetThreadTimes` accounting is quantized: sampled
per-stage CPU-time fields cannot resolve tiny stage waits and may produce
negative sampled wall-minus-work differences. Do not use those fields to infer
per-stage waiting. Use stage wall times/cycles and full-window CPU differences.

`D1R_GPU_PROFILE_LOG` enables hardware timestamps around frame GPU uploads,
rendering and the final swapchain blit. A 32-slot asynchronous ring polls fences
and reads completed queries without waiting for samples. GPU elapsed time
excludes CPU command recording, swapchain acquisition and DXGI presentation
wait; GPU preemption/stalls inside the interval can contribute. Dropped samples
are counted. Profiling is off during normal launches.

This pinned SDL revision has no public timestamp-query API. The bundled Windows
static SDL build compiles its unchanged D3D12 backend through a small owned
translation unit, exposing borrowed device/queue/command-list pointers. The game
does not duplicate or guess SDL private layouts. System/shared SDL and other
backends report native timing unavailable instead of estimating GPU execution.

The GPU trace also records cumulative main-thread CPU time and cycles. The
analyzer differences CPU-time endpoints across the full steady window, avoiding
per-stage accounting quantization. Wall minus CPU time includes waiting or
descheduling and does not identify the individual cause. Cycle counts are not
converted into CPU frequency or instruction counts.

## Repeatable measurement

`tools/ui_benchmark.py` prepares private fixed-scene version-3 replays from an
existing copied save, and rejects existing destinations. Inventory opens at tick
200. `tools/run_ui_benchmark.ps1` runs uncached/cached/cached/uncached controls,
then separate CPU/GPU profiles. All graphics tests remain muted on the left
display through the existing replay helper.

The tested replays contained 8,000 ticks. Analysis discards 15 seconds, then
selects complete one-second records contained within a subsequent fixed
20-second window (19 complete intervals in these runs). It rejects short runs
and checks for warm sprite decodes/page uploads. FPS controls use no capture,
hardware queries or thread-clock profiling; copied saves and settings are fixed.

| Capture-free steady control | Uncached FPS | Cached FPS |
| --- | ---: | ---: |
| First pair | 123.84 | 152.96 |
| Reversed-order pair | 111.86 | 146.21 |
| Final executable pair | 110.74 | 149.50 |

The initial pairs used the same inventory code before a logging-only refinement
to whole-window CPU accounting. The final pair and profiles use the final build.
These are scene-specific measurements, not a general FPS guarantee.

In the final instrumented profiles, main-thread CPU work occupied 98.8% / 99.5%
of the approximately 20-second windows. GPU execution averaged 0.864 / 0.899 ms
per frame, versus frame times of 8.54 / 6.68 ms. CPU UI wall time fell from
1.740 to 0.562 ms/frame; command submission fell from 1.203 to 1.072 ms/frame.
The cache captured/built once and replayed 7,737 times. No warm sprite decodes
or BC7 page uploads occurred in the selected windows.

The profiled scene is CPU-bound. Earlier short comparisons mixed inventory
opening/warm-up with steady rendering, and CPU drawing also varied between runs.
Longer matched windows expose a repeatable cache gain. They do not establish
the precise hardware/OS cause of all residual run-to-run variation; GPU saturation
and repeated sprite loading are not supported explanations for these runs.
CPU world traversal, lighting and submission remain substantial costs.

## Verification and installation

Owned synthetic readback checks cache hits, visual-state/palette invalidation,
translucency, opaque/blended overlap, cursor restoration, fractional viewport
resizing, retained HUD/progress layers and Classic fallback. Eager coverage and
uncached UI paths also pass. Hardware query traces have valid frequency/results
and no dropped samples in the validation runs.

The real cached inventory matched uncached captures pixel-for-pixel in the
reviewed 320x352 region. Both reference saves matched, and release/debug replays,
HD/Classic UI transitions, frontend and loading-bar checks passed. Installation
backs up both executables and rechecks existing compiled pages, authoring PNGs,
layouts, preferences and saves. The graphics pack is unchanged. Private artwork,
captures, saves and detailed trace/installation proofs remain outside Git.
