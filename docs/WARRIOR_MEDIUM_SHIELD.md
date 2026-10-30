# Medium warrior shield

The approved replacement is the user-supplied `shield_Medium.glb`. Keep its mesh
and textures private. Source identity and the approved forearm-local transform
are recorded in `tools/warrior3d/medium_shield_settings.json`.

The approved idle fit uses scale 0.75, a 30 cm upward adjustment and 25 degrees
of outward tilt. The arm pose is unchanged. The reference is the fresh 1200-pixel
close rotation from the medium-shield-clearance-v2 test, not an enlarged sprite.

Thirty medium sheets are being rebuilt: sword/shield, mace/shield and shield-only,
each with AS, AT, AW, BL, FM, HT, LM, QM, ST and WL. Keep other armor, weapons,
character motion and installed spell effects. Rebuild southeast shadows for the
new shield. Keep existing native grids and anchors; expand the canvas if needed
rather than cropping the new geometry or shortening the motion.

Use the equipment audit before and after `fit_medium_shield_clearance.py`.
The fit changes shield transforms only for poses that intersect the helmet.
All selected source poses must clear the helmet before installation. Run source,
frame-bound, BC7, isolated reference replay and live GPU checks. The installer
supports revision `medium-shield-v1` with backup/rollback and exactly 30 sheets.
Eight synthetic install/rollback tests passed, including this revision. A recipe
approval is not proof of installation: this revision is currently rendering.
