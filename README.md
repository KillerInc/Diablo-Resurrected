# Diablo Reincarnated

Current development build: **0.4.0-pre**. This project extends the existing DevilutionX-based engine with an optional HD renderer while retaining the original gameplay simulation and Classic mode.

Press **F10** in game to switch between Classic and HD. The renderer reads separately supplied graphics sheets from `hd/plrgfx`, `hd/monsters` and `hd/missiles`; original game data and replacement sheets are not included in this repository or its packages.

See [original-named sprite sheet support and validation](docs/HD_SPRITE_SHEETS.md) and the [0.4.0-pre change record](docs/releases/0.4.0-pre.md). `REINCARNATED_VERSION` controls the game's displayed version and Windows file/product version, independently of upstream save/network format versions.

Source, tests and build configuration are maintained here. Local checkouts are working copies for builds and testing. Windows build artifacts are produced by the [Windows x64 workflow](.github/workflows/windows-x64.yml).
