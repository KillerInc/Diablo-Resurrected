# v0.2 validation record

Validation date: 2026-10-20. Target: Windows 11 x64.

## Local source and package

Validated source tree: `581493622a8613fd5ef10f4eb198980aac9187d8`
(GitHub source commit `289c2008570f33af03cb6923b451e40f3882ecdc`).

- Visual Studio 2022 x64 Release build: passed.
- Renderer switch/layout, depth/zoom, and asset-provider tests: 3/3 passed,
  with assertions enabled in Release.
- Packaged AMD64 PE and `--version` startup: passed.
- Package dependencies: Windows system DLLs only; no external SDL2 DLL.
- Matching support MPQ: generated and verified, 184 assets, 5,263,903 bytes.
  Runtime log confirmed executable-adjacent `d1reincarnated.mpq` loading.
- Visual isolated replay: dungeon loaded; Classic, synthetic HD Warrior,
  readable Escape menu and return to Classic all inspected successfully.
- Accelerated Classic/HD/menu replay: 1,500 frames, exit code 0.
- Upstream Warrior gameplay replay: 4,853 frames, exit code 0, final save
  comparison reported "Same outcome as initial run."
- Normal menu flow: created a Warrior, entered town, typed its name with a
  physical key, moved with the mouse, switched F10, saved and loaded the game,
  then returned to Classic successfully.
- Existing installation save/config and checked DevilutionX preference/save
  file hashes remained unchanged. All test writes used isolated directories.

The Classic drawing implementation under `Source/engine/render/` is unchanged
from the v0.1 baseline. SDL3 startup, dependency configuration, support resource
lookup, replay events and validation tooling account for the migration fixes.

## Release artifact

[GitHub build 39478610994](https://github.com/KillerInc/Diablo-Resurrected/actions/runs/39478610994)
passed compilation, all three renderer tests, packaging and packaged startup.
Artifact `12291800240` was downloaded and its archive SHA256 verified:
`b57bb7ef8bedd644e8289c6fd88dd3bd432aaed5448a9d6fd57f104a1118a7ae`.

That exact artifact passed both accelerated replays (1,500 and 4,853 frames,
both exit code 0; reference save matched). Visual checks on the downloaded
executable also passed new Warrior creation, town loading, keyboard text,
mouse movement, F10 HD, menu visibility, save/load and Classic restoration.
The checked existing saves/config hashes remained unchanged afterward.

Validated executable SHA256:
`674eefaa55cd1833b91d2121c7c9c3d06482045dc16c4f8c57b37557fa39d966`.
The complete eight-file manifest is `.github/release-validation/v0.2.json`.
Publication uses that successful source build's artifact and verifies every
file hash before creating `v0.2-pre`; it does not rebuild the release files.

## Limits

These are launch and regression checks, not a full playthrough. Multiplayer,
controller coverage and audible sound quality have not been validated. HD
lighting and draw ordering remain experimental as in the v0.1 prototype.
