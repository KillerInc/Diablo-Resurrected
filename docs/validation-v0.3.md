# v0.3 validation record

Validation date: 2026-10-20 (America/Toronto). Platform: Windows 11 x64.
Source: `e90b0d150a8e1ba22f4b302d535c7f7d59bfc99b`. Build: [39529255804](https://github.com/KillerInc/Diablo-Resurrected/actions/runs/39529255804).

## Exact packaged game

- Windows x64 Release build, all four renderer/DDS tests, AMD64 PE check,
  support archive generation/verification and packaged `--version`: passed.
- Downloaded artifact `12314388971`; verified its archive SHA256:
  `5b3b055a04ab5339ad4a9ddfb45f83ce4efb14e0bd92750cebb74f5a2cb6f729`.
- Tested executable SHA256: `44675f9e7b170cca070b8625bc45f34f605c92a79944ffa364f239febfff7f76`. Its imports are Windows system DLLs;
  no external SDL2/SDL3 DLL or separate shader compiler is required.
- Runtime selected SDL_GPU `direct3d12` on AMD Radeon RX 7900 XTX. The SDL3
  window has one GPU presentation owner; no SDL_Renderer is created on it.
- Matching executable-adjacent `d1reincarnated.mpq` contains 184 engine assets
  (5,263,903 bytes). No original game data, user saves or settings are packaged.

The exact downloaded executable passed the extended 2,700-frame replay
(Classic, HD, Escape menu, cursor movement over/away from the menu, inventory,
character panel, 2x zoom, Classic restoration), exit code 0. GPU transfer-buffer
readback images were visually inspected for these states, including software
cursor placement and restored pixels beneath its old position.

A pixel comparison confirmed the CHAR-button HUD region matched Classic
restoration in every sampled zoomed frame (2150, 2250, 2350). A controlled
negative copy with the HUD removed was correctly rejected by the checker.

The 4,853-frame upstream Warrior gameplay replay also passed with HD enabled
and exit code 0. The replay traversed levels 1 and 2 and reported
`Timedemo: Same outcome as initial run. :)` for its final reference save.
Only two F10 presentation events were inserted after the tenth existing tick;
all original simulation ticks and gameplay events were retained. Mode logs and
GPU images confirm HD was active, rather than merely assuming F10 succeeded.

GPU images at gameplay frames 450 and 4150 show foreground wall/arch masks
covering or blending over the HD Warrior. Existing pre/post sprites, walking
source-tile corrections, and delayed foreground drawing remain in scrollrt's
original order, with no screen-Y global sort.

Separate copies of the exact executable passed valid loose RGBA DDS loading
and malformed-DDS fallback replays (1,500 frames each, exit code 0). Images and
logs confirmed the DDS Warrior loaded and the malformed image selected the
individual Classic Warrior while HD mode stayed active. Missing monster and
terrain artwork used their individual Classic rendering paths throughout HD
gameplay. The four foundation tests additionally cover BC1/BC2/BC3 decode,
truncated/oversized/invalid DDS rejection, provider precedence, switching,
submission order and zoom transforms.

The checked pre-existing installation save/config hashes remained unchanged.
All test writes used explicit isolated config/save directories. Complete
package file hashes are recorded in `.github/release-validation/v0.3.json`.
Publication verifies those hashes and uses this tested artifact without
rebuilding its files.

## Corrections and limits

A final review found cursor-only redraws needed RGBA cursor backing restoration
in addition to Classic's indexed restoration. This was corrected before this
source build was released; touch controls were also moved after composition.
The extended replay includes cursor movement while the HD menu is paused.

Composition is a CPU truecolor implementation; SDL_GPU performs upload,
scaling and swapchain presentation. This is not a shader-based HD rasterizer.
HD artwork and material lighting remain experimental; there is no BC7/.anim
builder. The loose DDS decoder supports RGB(A), BC1, BC2 and BC3.

Computer Use app approval timed out, so live desktop screenshots and physical
keyboard/mouse checks could not be completed. Visual inspection used frames
read back from the actual GPU texture. Desktop resizing/DPI/fullscreen,
hardware cursor, controller/touch interaction, audible quality, multiplayer
and a full playthrough remain unverified. Replay input and game loading/save
outcomes were tested directly.

SDL logged a missing optional `WinPixEventRuntime.dll` debug-marker diagnostic.
It did not prevent GPU creation, presentation, readback, or successful replay
completion; no PIX debug-marker calls are required by this implementation.

## Published pre-release

[Diablo Reincarnated v0.3 - Windows 11 x64 SDL_GPU (Pre-release)](https://github.com/KillerInc/Diablo-Resurrected/releases/tag/v0.3-pre)
was published by [workflow 39531920970](https://github.com/KillerInc/Diablo-Resurrected/actions/runs/39531920970).
The public ZIP was independently downloaded and all eight file hashes matched
the game-tested CI artifact. ZIP SHA256:
`e6f5882d65bad82703b3b10dafbe2dd514012a39240aad0096951d419a79113b`.

The first publication attempt passed artifact/file verification but GitHub
rejected release creation with HTTP 403. The successful publisher tags the
validation-record commit `8b2c1fcb21b5fc4838de7234456c42de6d671f24`,
after checking that its game/build inputs are identical to tested source
`e90b0d150a8e1ba22f4b302d535c7f7d59bfc99b`. Only documentation,
validation metadata and the standalone image checker may differ. The package
is the original tested artifact; publication does not rebuild the executable.
The v0.1/v0.2 baselines remain unchanged and PR #8 remains unmerged.
