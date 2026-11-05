# Controlled FPS investigation, 2026-10-31

## Method

Use `tools/run_fps_matrix.py` with a built SDL3 executable, a **private copy**
of a full-game slot-1 save/config/stash and a prepared version-3 `demo_7.dmo`,
and a new output directory outside Git. It requires PowerShell 7 and the
existing support MPQ beside the executable. No copyrighted inputs are supplied
in this repository.

The tool runs one game process at a time, hashes all fixture inputs and the
executable, creates separate case directories, changes only Graphics settings,
and verifies the original fixture hashes afterward. Audio is muted and test
windows open directly on the left secondary monitor. Capture is disabled.
The 720p case also changes the replay's resolution header. Gameplay settings,
game speed, character scale and installed art are not changed as optimizations.

Every run uses the same copied dungeon save and 900-frame input stream. The
scene contains 15 GPU actors including corpses and has the automap visible.
Aggregate FPS is derived from the last eight interval means weighted by frame
count, excluding preload/loading. Classic has fewer available warm intervals
because it finishes much faster; at least three intervals are required.
These are local scene measurements, not a general game benchmark.

## Comparison matrix before scan optimization

All rows use the same profiling executable
`152319B978E933145E9EC6C6DA0C59404EDBC11E29233B067D916EA0E4BF371C`.

| Single changed condition | Warm FPS | Frame ms |
| --- | ---: | ---: |
| HD, 1920x1080, zoom on, per-pixel lighting on: first control | 73.17 | 13.67 |
| Classic | 277.09 | 3.61 |
| Per-pixel lighting off | 80.44 | 12.43 |
| HD GPU actor draws disabled, Classic actor fallback | 73.61 | 13.58 |
| Zoom off, showing more terrain | 36.44 | 27.44 |
| 1280x720 | 144.26 | 6.93 |
| Unchanged HD settings: second control | 71.61 | 13.96 |

Mode and cumulative GPU draw counts confirm the Classic/disabled-actor controls
actually take effect. Lighting is timed both during lightmap creation and as
part of the subsequent tile rasterization. Its total cost is not just the
`lighting` stage.

## Where CPU time goes

Representative first-control means in milliseconds per frame:

| Stage | CPU ms |
| --- | ---: |
| Floor rasterization and HD mirroring | 2.90 |
| Tile contents, including walls, actors and occlusion | 3.73 |
| Lightmap creation | 0.58 |
| Frame setup/clearing | 0.61 |
| Remaining world work/zoom | 0.31 |
| View UI, including automap | 0.61 |
| Main HUD and cursor | 0.18 |
| Supplemental scan for raw indexed UI writes | 1.71 |
| Classic/world copies and UI blending | approximately 1.30 |
| Frame upload preparation | 0.31 |
| Acquiring a swapchain image | 0.03 |
| HD actor GPU command preparation | 0.21 |
| Command submission | 0.57 |

These are CPU wall timings. GPU commands execute asynchronously; the figures
are not GPU execution timestamps. They account for instrumented renderer work,
not every part of the game loop. Low aggregate CPU usage does not rule out a
busy serial rendering thread.

The disabled-actor test and small display wait provide evidence against HD
actor GPU execution or a refresh-rate cap being the dominant cost in this
scene. The large increase when more terrain is visible points to CPU terrain
rasterization and its HD mirror as the largest remaining target. Lowering
resolution or disabling lighting is a diagnostic control, not a shipped fix.

## Instrumentation

Set `D1R_CPU_PROFILE_LOG` to an isolated output CSV path to enable the detailed
CPU stage collector. The ordinary performance log is unchanged. Stage records
contain timestamp, stage name, frame count, call count, total CPU milliseconds,
milliseconds per frame and microseconds per call. Inactive/loading windows reset
the counters. No profiling file is created on a normal launch without this
environment variable.

`D1R_PROFILE_HD=1` separately logs raster span counts and actor preparation time.
Neither feature reports true GPU utilization or execution time.

The performance overlay labels average, p95 and maximum frame time with `ms`
beside each value. For example, 170 FPS corresponds to about 5.9 ms per frame;
an average frame-time value of 5 is milliseconds, not 5 FPS.

## Safe optimization tested

The supplemental UI pass previously compared every indexed pixel in the
viewport, even where no UI had been drawn. Entire unchanged rows can be
rejected with a bulk comparison. The automap touches many rows, so the final
candidate also rejects unchanged 64-pixel blocks within changed rows. Only
changed blocks run the original pixel comparison and coverage fallback.

This preserves raw UI writers, equal-color raster coverage, clipping and short
tail blocks. Regression fixtures cover raw writes across block boundaries,
the viewport edges and unchanged pixels. It changes no graphics settings,
sprite resolution, animation timing, lighting or game speed.

Whole-map/chunk caching and GPU-native terrain drawing remain larger future
changes. They must preserve dynamic lighting, doors, tile animations, actor
occlusion and foreground ordering.

## Optimization measurements

Two runs of the block-based candidate before the cosmetic `ms` label change,
with the original HD settings:

| Run | FPS | Frame ms | Compose CPU ms | Raw UI scan CPU ms |
| --- | ---: | ---: | ---: | ---: |
| First | 81.12 | 12.33 | 1.72 | 0.459 |
| Second | 80.03 | 12.50 | 1.78 | 0.472 |

Before this final refinement, a repeat of the original profiling executable
returned 71.6 FPS. The two initial controls returned 73.2 and 71.6 FPS. The
final improvement exceeds that observed variation, although the exact gain
will depend on scene and UI activity. The row-only intermediate returned
75.3 and 73.5 FPS and was less effective with the automap visible.

All timing comparisons run sequentially without capture or another game test
in parallel. The same copied save, inputs, resolution, zoom, per-pixel lighting
and installed pack are retained. This does not promise the same FPS elsewhere.

The measured candidate above had normal executable SHA-256
`24F619671FC5EC3F0470144F4B873507E96267CC31FAA55D4F3E8779FA226ED9`.
The final `ms` label build was measured again with the same controls: **81.14
and 80.67 FPS**, average frame times **12.325 and 12.396 ms**, and raw UI scan
times **0.488 and 0.503 ms**.

Final `0.4.10-pre` executable SHA-256 values:

- Normal: `C7D45FB2906030954C6003B879A573779841786CB9ED2C6CDD6C4A06DA4CD2DA`
- Debug: `8EF5516A7EA60C23D09474258D8B08725658DD2887CD39C2E5A7B57FDFF78018`

## Regression and installation checks

- Independent scalar raster/lighting/blend comparisons and synthetic GPU
  readback, including occlusion, native output resolution and cursor restore.
- Retained HUD reset/dirty/overlay checks and raw UI writes across 64-pixel
  block boundaries, clipped edges and a short final block.
- Performance-overlay unit check for the explicit `avg 20.0 ms` label.
- Both reference saves retain their original final outcomes.
- F10/F11, menu overlay and saved-HD startup replays.
- Matching Debug companion developer-console replay.
- Selected-class preload remains pinned at 255 Warrior sheets, with no CPU HD
  PNG decodes or warm player reloads. Existing full BC7-pack proof and hashes
  are retained; no sprite or layout data is changed.

Installation backs up both previous executables and checks existing pack,
authoring PNG and layout hashes. User settings and saves are preserved.
Only code, test tools and this sanitized report are published; private saves,
artwork, model files and captures remain outside Git.
