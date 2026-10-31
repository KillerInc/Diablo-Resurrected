# BC7 world sprites and saved rendering mode

Version 0.4.8-pre extends the existing Warrior BC7 pipeline to the remaining
installed world sheets: 510 Rogue/Sorcerer sheets, 186 monster sheets and 151
missile sheets. The 255 previously approved Warrior records and pages remain
unchanged, for 1,102 compiled sheets altogether.

SDL3 HD world sprites load only compiled BC7 resources. Missing or unsupported
compiled resources retain Classic rendering; they never trigger a PNG decode.
Original PNGs remain private authoring inputs and are preserved during installation.
Normal engine UI images and screenshot output are separate from HD world sheets.

`HD/sprites.gpus` remains the sole compiled index, cached until process exit.
Its `.png` record names are logical sprite identifiers, not PNG file reads.
The selected player's class is discovered from this index, so preloading works
without PNG files in the runtime pack. The shared `HD/layouts.csv` still provides
logical anchors. Executable/data/current-directory aliases are mounted once to
avoid loading the same physical index repeatedly.

Player sheets preload by class. Monster and missile pages load when first needed
and remain cached until the game session ends. Performance metrics count all GPU
sheets separately from the selected player-class count; CPU sprite decode/cache
bytes stay zero. F10 and display resets preserve GPU resources and index caches.
The existing shader applies monster TRN recolouring, lighting, blending and
foreground coverage to these additional sheets.

Graphics settings now include **HD Graphics**. F10 updates the same setting and
saves it immediately in normal play. Startup restores `[Graphics] HD Graphics`
(`1` for HD, `0` for Classic); an absent setting keeps the previous Classic default.
Replay tests continue to avoid writing user settings.

## Offline conversion

1. Use `tools/inventory_gpu_sprites.py` with the installed HD directory and the
   user's extracted original CL2 directory. Grids come from the original files,
   including single-list missiles and varying direction frame counts.
2. Run `tools/pack_gpu_sprites.py --inventory ...` with disjoint inventory slices
   and separate proof filenames. All writers must finish before consolidation.
3. Run `tools/gpu_index.py NEW_PACK/HD --base-index EXISTING_HD/sprites.gpus` to
   preserve existing records while adding the new sheets.
4. Use `tools/validate_world_gpu_pack.py` to check every new page through a real
   BC7 decoder, source identities, grids, frame bounds, anchors, preserved base
   records/pages and sampled colour/alpha quality.
5. Upload the complete PNG-free pack using `reincarnated_gpu_pack_upload_test`.
   It exercises the runtime loader for every record while retaining one sheet at
   a time, rather than loading every class into VRAM together.

The new pages retain native-4x density, matching the approved Warrior pack.
No model, animation, PNG or game-data files belong in Git.

## Builds and checks

`tools/build_debug_companion.ps1 -Configuration Release` builds the normal
executable in a separate directory. Its default Debug configuration builds the
separately named companion. Both use the same renderer and saved-mode setting.

Focused targets cover compiled provider namespaces/discovery, PNG-free Classic
fallback, actual GPU lighting/TRN/occlusion readback, saved-mode round trips and
full-pack GPU uploads. Final installation also requires two matching gameplay
reference replays, F10/F11 checks, saved-HD startup, unchanged source hashes and
unchanged user saves/settings. Test audio stays muted in isolated configurations.
