# Raster batching and retained HUD, 0.4.9-pre

The widescreen path previously forced the main panel, lower flasks, buttons,
spell icon and belt to redraw every frame. HD now draws those components into
a separate persistent indexed HUD backing surface. An RGBA copy is rebuilt
when components change and composited over the world each frame. Existing
component dirty flags determine which elements need drawing.

Transient UI remains on the separate frame UI overlay: inventory and character
panels, automap, menus, messages, hover information, upper flasks, FPS display
and cursor. These can change or expose the moving world, so they continue to
refresh. The retained HUD is composited before final information text, chat,
values and cursor drawing. Transient pixels never feed back into its backing
surface. Palette, screen size, panel position and renderer resets invalidate
the retained HUD. Classic keeps its existing redraw path.

This is separation and retention of the main HUD, not caching every UI screen
or moving all composition to GPU textures. The visible world and final frame
still render each frame; no terrain cache was introduced.

## Other renderer work in this build

- Replace per-pixel RGBA mirror calls with clipped opaque/blended spans,
  specializing the existing 1x/2x world zoom. Integer 50% blends retain the
  exact per-channel floor result.
- Partition GPU actor coverage into 32x32 screen bins so terrain writes visit
  nearby actor masks instead of every queued sprite. Bins do not change image
  resolution, draw order, lighting, sprite scale or game speed.
- Add opt-in `D1R_PROFILE_HD=1` counters for spans and actor preparation time.
- Reconfigure automatically when `REINCARNATED_VERSION` changes.
- Add `tools/run_sprite_perf_probe.ps1` for prepared isolated full-game replays.
- Test runners request `D1R_TEST_DISPLAY=left`. SDL window creation positions
  test windows on a secondary display left of the primary before first show.
  The verified display was at `-1920,130`, size `1920x1080`. Normal launches
  leave window placement alone. Test audio is muted in isolated settings,
  with the existing 0.5 test master gain also retained.

## Validation

Release and Debug companion builds report `0.4.9-pre`.

| Executable | SHA-256 |
| --- | --- |
| Normal | `B0D894FD7F2895BCB735D2CEDC35DAB3566DB1D10F3FEF55105ADA65257AB8EC` |
| Debug | `0D943AD1FB1D25CFDF22C57E82A69BDFDA1417C39F0FF7590FD4F76BC095BFAF` |

Passed checks:

- Independent scalar-reference raster comparison for zoom, clipping, offsets,
  translated/per-pixel lighting and repeated UI blending.
- Retained HUD survival across new world frames, dirty updates, transient
  overlay exclusion, cursor restoration, palette/position invalidation,
  renderer reset and Classic fallback.
- GPU readback for compressed sprites, lighting/TRN, ordered opaque and
  blended occlusion, cursor restoration and physical-resolution output.
- Asset-provider and saved renderer-mode tests.
- Both reference-save replays retain the original final save outcome.
- UI replay switches F10/F11 and opens the menu; saved-HD startup restores HD.
- Debug companion executes its developer Lua module and reversible god-mode
  commands in an isolated replay.
- PNG-free test pack retains all 1,102 compiled records, 2,767 BC7 pages and
  8,782,036,992 texture bytes. Selected Warrior class loads/pins 255 sheets,
  without CPU HD sprite buffers, warm player uploads or other-class preload.
  Prior full-pack upload proof remains applicable: pack data is unchanged.
- Private captures of the widescreen scene and menu were inspected. Artwork,
  captures, models and saves are excluded from Git.

The provider test requires normal access to its temporary fixture directory;
its restricted-process run terminated, and its unrestricted rerun passed.

## Local timing sample

Same copied save and 900-frame input replay, 1920x1080, zoom enabled, 15 GPU
actors including corpses. Means below weight the last eight interval rows by
frame count; loading and class preload are excluded.

| Build | FPS | Frame ms | Draw CPU ms | Compose CPU ms | Present CPU ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Installed 0.4.8 baseline | 32.72 | 30.57 | 23.58 | 3.09 | 1.36 |
| Raster batching candidate | 68.95 | 14.50 | 8.85 | 3.07 | 1.28 |
| Final retained-HUD build | 70.09 | 14.27 | 8.79 | 3.49 | 1.17 |

Most of this improvement comes from raster batching and spatial coverage.
The small additional FPS difference is within normal run variation; it is not
an isolated measurement of the HUD cache. The final test used the left-hand
monitor, was profiled without frame capture and ran without another game test
in parallel. These CPU wall timings are not GPU execution timings and do not
promise 110 FPS in other scenes.

Installation backs up both previous executables and verifies existing PNG,
BC7 and layout hashes. Normal user settings and saves are preserved. Source
and build files remain in the working checkout, not the game installation.
