# Project working agreement

- GitHub is the durable record of this project. Keep completed source changes, tests, build configuration and validation documentation committed and pushed to the working branch. Report the remote commit rather than leaving the only copy in a local working tree.
- Local source checkouts and build files are temporary tools for implementation and testing. Do not install source into the game directory or keep extra source copies as deliverables. Keep a checkout only while it is needed for active work or validation.
- The installed graphics sheets are user-supplied reference/test inputs. Never commit or upload them. Do not include screenshots/captures containing that artwork, extracted original game data or saves in repository commits or public build artifacts. Synthetic test fixtures and the repository's existing open-source engine assets remain suitable for version control.
- Preserve installed game data, sheets, preferences and saves. Back up an installed executable before replacing it with a tested build.

- Since 0.4.3-pre, `HD/layouts.csv` is the only runtime layout source. It is cached until process exit; F10 does not reload it. Do not install individual `.layout` files into the game HD tree. Update the CSV atomically using `tools/hd_layouts.py` helpers and verify PNG hashes/anchors. Offline render outputs and private backups may retain sidecars. Legacy install scripts must be adapted before reuse.

- Since 0.4.4-pre, initial SDL3 save/new-game loading preloads and session-pins all installed sheets for the selected sprite class. Preserve pins across F10/level/display resets and release them on game exit; keep MPQ discovery serial and PNG workers bounded. Validation must check resident count/bytes, no warm player redecodes, reference-save outcomes, and current PNG/CSV hashes.

- Since 0.4.5-pre, F11 toggles the performance overlay and active gameplay emits interval metrics to the config-directory performance.csv. Preserve loading/inactive exclusions, CPU/RAM versus GPU/VRAM labeling, and F10/player cache behavior. Validate CSV values and F11 toggles alongside reference replays before installing renderer updates.
