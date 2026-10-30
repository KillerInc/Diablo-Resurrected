# Equipped Warrior casting

The equipped FM, LM and QM sheets use native Paladin Aura Fanaticism motion.
Weapons and shields remain held throughout the cast. Unarmed casting keeps
the previously approved Gizmo motion. Other actions and heavy armor are outside
this revision; the installed executable remains 0.4.7-pre.

## Motion and equipment

- Light and medium armor each have 24 equipped casting sheets: axe, bow,
  sword/shield, mace/shield, mace, sword, staff and shield-only, with three spells.
- Axe, staff and bow use `palM_2HM_aura_fanaticism`; one-handed equipment and
  shield-only use `palM_1hsShd_aura_fanaticism`.
- Each complete native clip is sampled into the existing runtime sheet grid.
  Donor frame counts must never determine the installed sheet row count.
- Character geometry, scale, arm motion, approved grips and equipment models
  are preserved. The shield and bow rotate rigidly around their grip points
  where necessary for head clearance. The bowstring is evaluated together with
  the bow; testing only its unmodified mesh coordinates misses its final shape.
- Preserve the fire bubble, lightning and approved two-emitter blue particle
  effect settings, including dispersal, radius and particle count.
- Preserve southeast shadow projection. Expand transparent canvas bounds for
  complete body, weapon, particle and shadow coverage instead of reducing motion.

## Reproducible private workflow

All models, animation data, PNGs, GPU pages, previews and captures remain private.
Only these tools and this record belong in Git.

1. `warrior3d/prepare_equipped_casts.py` takes the native animation collection,
   current light motion catalog, approved medium plan, fresh work directory and
   current GPU proof containing the authoritative native grids.
2. Run `warrior3d/fit_cast_head_clearance.py` in Blender. Its grip-preserving
   search checks every integer source frame, including evaluated bowstring
   geometry. It does not change the skeleton or animation.
3. Run the bounds preflight and `warrior3d/audit_medium_equipment.py`; inspect
   every reported head contact before rendering. The head audit supports the
   light head and medium head/helmet separately.
4. Run the existing batch renderer with a private plan. Disjoint workers may
   render different jobs. Identical shadow poses can reuse exact rendered
   shadows even when their spell effects differ. This does not affect body
   rendering or spell emission masks.
5. `warrior3d/compile_equipped_casts.py` stages the complete baseline class,
   compiles changed sheets and creates the root GPU index after all jobs finish.
   Re-running it detects corrected output hashes rather than trusting stale
   completion records. Never run multiple compilers against one staging pack.
6. Validate all 255 GPU sheets and sampled compression against the staged PNGs,
   run the isolated reference/UI replays, and review actual GPU-rendered casts.
   `prepare_cast_live_test.py` aliases visuals in a separate test pack; it never
   edits save statistics. Its test-only row sampling is not installed.
7. `validate_equipped_casts.py` binds bounds, head-clearance and visual proofs
   to replay results, verifies all 207 unaffected sheets and checks user state.
8. With the game closed, `install_equipped_casts.py` backs up replaced files
   and updates only the 48 approved casting sheets, BC7 pages and root metadata.
   `test_install_equipped_casts.py` exercises successful installation and rollback
   after obsolete page retirement. `archive_equipped_casts.py` preserves complete
   reproducible inputs, source sheets, reviews and the verified GPU pack privately.

The only runtime metadata files remain `HD/layouts.csv` and `HD/sprites.gpus`.
Both retain their existing process-lifetime caching. Tests use half-volume audio
without changing the user's saved volume settings.

## Verification status

Installed graphics revision `equipped-casts-v1` on 2026-10-30. All 48 sheets
cover 7,688 directional body/shadow frames. All 48 equipped sequences pass
head/helmet clearance. Runtime grids retain 20 rows, except the medium
sword/shield lightning sheet's original 21 rows. All 207 unaffected source PNGs
are byte-identical to the prior pack, including every unarmed and heavy sheet.

The full class validates across 255 sheets and 867 BC7 pages totaling 2.726 GiB.
All pages decode; 170 compression samples pass, with worst visible RGB RMSE
2.4358 and alpha RMSE 2.2727 on the 0-255 scale. All current render hashes match
the final compiled manifest. Two 4,853-frame reference-save replays produce the
same outcomes. F10/F11/UI, actual equipped-cast GPU draws, process-cached
metadata, zero retained CPU player RGBA and zero warm page uploads pass.
The normal GPU pack and isolated visual-alias pack use their own verified page
counts; aliases and visual-only row resampling are never installed.

The transactional installer backs up replaced PNGs/pages and retires obsolete
casting pages only. Synthetic success and rollback-after-retirement tests pass.
The private archive preserves four complete animated character models, two
exact compact motion donors, seven equipment assets, all references/calibration,
48 source sheets/review GIFs, actual in-game captures and the full GPU pack.
The current 85-entry light motion catalog points to archived inputs for future
armor rebuilds. No proprietary artwork or raw motion is published in Git.

The replay using the installed executable also matches the reference outcome.
Installed PNG/GPU hashes, all 207 preserved sheets, saves/settings, the unchanged
executable and the single runtime index/table pass the final integrity check.

## Fire revision installed 2026-10-30

`fire-bubble-v2` replaces all 18 light/medium FM sheets, including unarmed.
It enlarges the voids in the bubble and fixes the shell at the cast-start location.
Character motions, equipment and all 2,880 directional shadow images are unchanged.
The full class remains 255 sheets and 867 BC7 pages, using 2,924,388,352 texture bytes.
Two reference replays, UI/F10/F11, actual cast GPU draws and the installed-executable
smoke replay passed. The executable remains 0.4.7-pre and user state is unchanged.
The private archive is `Warrior Fire Bubble Approved 2026-10-30`.

Lightning plasma experiments were reviewed and rejected. Keep the currently
installed legacy lightning; `lightning_settings.json` selects that existing mode.
No plasma experiment was installed. Graphics replays mute music, effects and cues
in their isolated test INI; normal saved settings and Windows volume stay unchanged.
