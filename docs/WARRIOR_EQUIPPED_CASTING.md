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

Production rebuild and installation checks are in progress. Do not interpret
preview approval or completed preparation as a completed installation.
