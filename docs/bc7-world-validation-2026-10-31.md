# BC7 world sprites validation — 2026-10-31

Version: 0.4.8-pre, Windows x64 SDL3. Both normal and Debug executables installed.

- Normal SHA-256: `9430EC18A192CDFE4E0B9646E9D2D710CBED995101991E58D656ECAF0837986E`.
- Debug SHA-256: `C10209E02882C447D69477BBB02A5E277DC281B2C1E6760B5792031E9938C99B`.
- 847 newly compiled sheets: 510 Rogue/Sorcerer, 186 monsters and 151 missiles.
- 255 existing Warrior records and BC7 pages preserved unchanged.
- Combined pack: 1,102 sheets, 2,767 pages, 8,782,036,992 BC7 texture bytes (8.179 GiB).
- Every page decoded offline and uploaded through the actual GPU loader from a pack containing no HD PNGs; upload validation retained one sheet at a time.
- All original CL2 grids, source PNG hashes, frame bounds and the shared anchor table verified.
- 26 colour/alpha quality samples passed the 20/255 RMS threshold.
- Two complete Warrior gameplay replays matched the reference save.
- Zero CPU HD sprite PNG decodes/cache bytes; selected-class preload remained 255 sheets.
- Single process-lifetime root-index read, F10/F11 behavior and no warm player uploads verified.
- Saved HD/Classic round trips, startup in saved HD mode and pack override priority passed.
- Final installed normal/Debug launches and Lua developer-console checks passed with isolated saves and muted test audio.
- Original PNGs/layouts preserved; executable/index backups retained privately.

The full pack size is not the runtime preload allocation: only the selected player
class preloads; monster and missile pages are cached on demand. Other player
classes are not preloaded in the Warrior tests.

User preferences were not reset. The normal INI and save files changed during the final phase;
test logs confirm isolated save/configuration directories, and the current user
files were preserved. Private images, saves, game data and pack files are excluded from Git.
