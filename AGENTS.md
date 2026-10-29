# Project working agreement

- GitHub is the durable record of this project. Keep completed source changes, tests, build configuration and validation documentation committed and pushed to the working branch. Report the remote commit rather than leaving the only copy in a local working tree.
- Local source checkouts and build files are temporary tools for implementation and testing. Do not install source into the game directory or keep extra source copies as deliverables. Keep a checkout only while it is needed for active work or validation.
- The installed graphics sheets are user-supplied reference/test inputs. Never commit or upload them. Do not include screenshots/captures containing that artwork, extracted original game data or saves in repository commits or public build artifacts. Synthetic test fixtures and the repository's existing open-source engine assets remain suitable for version control.
- Preserve installed game data, sheets, preferences and saves. Back up an installed executable before replacing it with a tested build.

- Since 0.4.3-pre, `HD/layouts.csv` is the only runtime layout source. It is cached until process exit; F10 does not reload it. Do not install individual `.layout` files into the game HD tree. Update the CSV atomically using `tools/hd_layouts.py` helpers and verify PNG hashes/anchors. Offline render outputs and private backups may retain sidecars. Legacy install scripts must be adapted before reuse.

- Since 0.4.4-pre, initial SDL3 save/new-game loading preloads and session-pins all installed sheets for the selected sprite class. Preserve pins across F10/level/display resets and release them on game exit; keep MPQ discovery serial and PNG workers bounded. Validation must check resident count/bytes, no warm player redecodes, reference-save outcomes, and current PNG/CSV hashes.

- Since 0.4.5-pre, F11 toggles the performance overlay and active gameplay emits interval metrics to the config-directory performance.csv. Preserve loading/inactive exclusions, CPU/RAM versus GPU/VRAM labeling, and F10/player cache behavior. Validate CSV values and F11 toggles alongside reference replays before installing renderer updates.

- Since 0.4.6-pre, the installed Warrior class has 255 compiled native-4x BC7 GPU sheets. Preserve original PNGs and HD/layouts.csv; GPU frame records carry crop/page coordinates while logical anchors still come from the single cached CSV. Keep pages bound to their metadata provider and resident across F10/levels; release class pages on game exit. Preserve Classic/CPU and virtual-gamepad compatibility. Do not retain full CPU player RGBA when compiled resources are available. Validate actual GPU draws, synthetic native-resolution/lighting/occlusion readback, warm-upload counts, two reference saves, UI and source hashes before installing.
- Run test audio with D1R_TEST_AUDIO_GAIN=0.5 (tools/run_gpu_replay.ps1 does this). Never reduce the user's normal saved volume settings for test convenience.

- Since 0.4.7-pre, `HD/sprites.gpus` is the sole runtime compiled-sheet index, cached per provider until process exit. Keep shared defaults in the index with explicit per-sheet exceptions; do not restore individual runtime `.gpus` reads. Finalize the index after parallel encoders finish. Preserve BC7 page hashes and back up retired metadata during installation.
