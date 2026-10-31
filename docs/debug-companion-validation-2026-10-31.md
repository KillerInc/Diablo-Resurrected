# Debug companion validation — 2026-10-31

Version: 0.4.7-pre, Windows x64 SDL3, standard Debug configuration.

- Separate `Diablo Reincarnated Debug.exe` installed beside the normal executable.
- Debug executable SHA-256: `D3F467C5F8737945F656691B9CF220E231DC3C344DBFAE385AB2105001D8B46A`.
- Normal executable SHA-256 unchanged: `E3DEEB1BF5F5F1A9AACEF0F47647AD3FE392920CE41EDF6F3E085A27A0339D94`.
- Lua developer module, gold API presence and reversible god-mode toggle passed in an isolated save.
- Two complete gameplay replays matched the reference-save outcome.
- HD/Classic (F10) and performance-overlay (F11) replay toggles passed.
- Each test loaded 255 Warrior GPU sheets, 897 BC7 pages and 3,024,617,472 texture bytes.
- Actual HD GPU draws confirmed; no CPU player PNG decodes or warm GPU page uploads.
- Single process-lifetime compiled index read per test confirmed.
- All 255 installed player PNGs, 897 BC7 pages, root index and layout hashes matched the approved pack.
- Normal support archive, user save files and settings remained unchanged.
- All graphics tests used isolated configurations with music, effects and cues muted.

The Debug configuration is slower than the normal build. The replay runner now
accepts `-TimeoutSeconds` for diagnostic builds; its normal 360-second default is
unchanged. Private logs, saves, images and game assets are not included in Git.
