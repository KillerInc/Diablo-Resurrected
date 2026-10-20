# Windows 11 x64 SDL3 v0.2

Development branch: `feature/windows-x64-sdl3-v0.2`, based on the head of
the existing v0.1 draft PR #6. The v0.1 branch and release are not modified.

## Rendering and data

The existing DevilutionX CPU framebuffer, palette conversion, sprite drawing,
lighting, and world traversal remain the Classic renderer. SDL3 supplies the
Windows window, input, audio, and presentation backend. This does not replace
the Classic algorithms with GPU drawing.

F10 still switches Classic / experimental HD, ignoring held-key repeats.
HD uses the existing PNG provider and synthetic Warrior fallback, with Classic
fallback while the Escape/options menu is open. HD lighting and world draw
ordering remain experimental. The `.anim` format is not part of this migration.

The independent executable remains `Diablo Reincarnated.exe`. Its support
archive is `d1reincarnated.mpq`, generated from the matching staged source
assets, including `ASSETS_VERSION`. Windows preferences and saves remain under
SDL's `KillerInc/Diablo Reincarnated` preference directory. Nearby DevilutionX
`diablo.ini` files do not override that isolation. Explicit `--save-dir` and
`--config-dir` overrides remain available.

## Build

Use Visual Studio 2022 C++ tools, CMake 3.22 or newer, Python 3, and vcpkg.
The Windows workflow contains the complete x64 static dependency configuration.
The SDL3 feature in vcpkg supplies libpng; SDL3, SDL3_image, and SDL3_mixer are
the existing hash-pinned source dependencies. SDL2 is not selected by that build.
The `USE_SDL3` flag must be ON, with system SDL3/image/mixer disabled and their
static options enabled. The upstream target name remains `devilutionx`.

For deeply nested local checkouts, set `VCPKG_INSTALL_OPTIONS` to
`--x-buildtrees-root=<short temporary path>` to avoid Windows compiler path
limits. Keep `CMAKE_MSVC_RUNTIME_LIBRARY` consistent with `x64-windows-static`.

## Validation and publication

Renderer foundation tests run in Release with assertions enabled. Packaging
checks the AMD64 PE header, generates and verifies the support MPQ, includes
the synthetic Warrior and SDL licenses, and runs the packaged `--version`
entry point with a timeout. That startup check does not prove game loading.

For a reproducible local game test, run:

```text
python tools/create_sdl3_validation_demo.py --out <isolated-test-folder>
"Diablo Reincarnated.exe" --spawn --diablo --demo 1 --save-dir <isolated-test-folder> --config-dir <isolated-test-folder> --data-dir <owned-Diablo-folder> --verbose --log-to-file <test-log> -n
```

Run from the extracted package folder. The replay loads an upstream test
Warrior and holds each phase for 15 seconds: Classic, HD, Escape menu, HD,
Classic, then exits. `--timedemo` exercises the same sequence without waiting.
Logs report F10 transitions and successful HD texture loads. Visually inspect
the menu, Warrior, and Classic restoration as well as checking the exit code.
Also test the normal main menu, input, audio, settings, and save/load paths.

Game data is used only locally and must never enter the package or repository.
The CI artifact is named `Diablo Reincarnated v0.2`. A GitHub pre-release may
be published only after the exact package has passed game-launch validation.
The development workflow deliberately does not publish on each snapshot.
