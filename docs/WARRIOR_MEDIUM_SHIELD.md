# Medium warrior shield

The approved replacement is the user-supplied `shield_Medium.glb`. Keep its mesh
and textures private. Source identity and the approved forearm-local transform
are recorded in `tools/warrior3d/medium_shield_settings.json`.

The approved idle fit uses scale 0.75, a 30 cm upward adjustment and 25 degrees
of outward tilt. The arm pose is unchanged. The reference is the fresh 1200-pixel
close rotation from the medium-shield-clearance-v2 test, not an enlarged sprite.

Thirty medium sheets are installed: sword/shield, mace/shield and shield-only,
each with AS, AT, AW, BL, FM, HT, LM, QM, ST and WL. Keep other armor, weapons,
character motion and installed spell effects. Rebuild southeast shadows for the
new shield. Keep existing native grids and anchors; expand the canvas if needed
rather than cropping the new geometry or shortening the motion.

Use the equipment audit before and after `fit_medium_shield_clearance.py`.
The fit changes shield transforms only for poses that intersect the helmet.
All selected source poses must clear the helmet before installation. Run source,
frame-bound, BC7, isolated reference replay and live GPU checks. The installer
supports revision `medium-shield-v1` with backup/rollback and exactly 30 sheets.
Eight synthetic install/rollback tests passed, including this revision. The
synthetic canvas test also verifies unchanged world registration after padding.

## Installed validation, 2026-10-30

All 30 sheets passed body/shadow bounds and helmet-clearance checks. Transparent
padding was added where needed; no character scale or motion was reduced.
All other 225 PNGs, their GPU pages, index records and layout rows were verified
unchanged against the installed fire-bubble-v2 baseline. The complete pack has
255 sheets, 868 BC7 pages and 2,923,126,784 texture bytes at density 4.

Two reference-save replays produced the original outcome. UI/F10/F11, GPU cache
residency, live medium-image GPU draws and the installed-executable smoke replay
passed. CPU player PNG decodes and warm GPU uploads remain zero. Normal user
state and the 0.4.7-pre executable are unchanged. Test music, effects and cues
were muted only in isolated replay configurations.

Final PNG/GPU hashes and the single runtime index/CSV were verified after the
transactional install. The private archive is `Medium Warrior Shield Approved
2026-10-30`; the rollback backup is `Backups/medium-shield-2026-10-30` in the game
directory. The canonical medium rebuild plan now references the archived recipes.
No model, animation, texture, sprite, capture or save data is stored in Git.
