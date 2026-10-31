# Diablo Reincarnated Debug companion

The optional developer build produces `Diablo Reincarnated Debug.exe`. The normal
build still produces `Diablo Reincarnated.exe`. Both use the existing installed
game data, HD pack and default save/configuration directory. Renaming an ordinary
release executable does not enable the console.

Run `tools/build_debug_companion.ps1` from PowerShell after preparing the normal
Windows x64 SDL3 dependency build. It creates a separate Debug build directory,
reuses dependency sources and installed static libraries, and enables the
existing `_DEBUG` Lua console. It does not install or replace any game files.
Install only the resulting companion executable beside the normal executable;
keep PDBs, sources and build directories out of the game folder.
For a test outside the game folder, copy the existing `d1reincarnated.mpq` beside
the test executable too: support archives are intentionally resolved relative
to the executable, even with `--data-dir` pointing at the installed game.

In a loaded game, press the backtick/grave key below Esc to open the console.
Examples:

```lua
dev = require("devilutionx.dev")
dev.player.god(true)
dev.player.god(false)
dev.player.gold.give(10000)
```

These are Lua console commands, not chat commands. Cheats can change the current
character and its saved state. The companion shares normal saves by default;
use `--save-dir` and `--config-dir` for isolated experiments. F10 still switches
HD/Classic rendering and F11 still toggles the performance overlay.

The executable uses the standard Debug configuration and may run slower than the
normal build. It retains the current project version; its filename, Windows
description and debug resource flag distinguish it from the normal executable.
