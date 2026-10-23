# Warrior 3D prototype

Editable, procedurally built light-armor, unarmed Warrior. This is a rig/export feasibility prototype, not finished Diablo artwork or a replacement for the installed sprites.

## Contents and status

- `models/warrior/Warrior-Light-Unarmed.blend`: editable source scene, 74 meshes, 18 bones, idle (10 frames) and walk (8 frames), plus loop endpoints.
- Eight orthographic directions, transparent 768-pixel cells; exporter produces `wlnas.png` (6144 x 7680) and `wlnaw.png` (6144 x 6144).
- Both animation loops and all 144 exported cells passed structural validation. GLB is a portable rig/mesh derivative; Blender procedural material details are not baked into it.
- Visual fidelity is **not accepted**: mean body-mask overlap is approximately 37% in the initial two-pauldron prototype for both actions. Anatomy, stance, clothing, materials and animation require substantial refinement against the NN8 references. This prototype does not cover town actions, attacks, spells, damage, death, other armor, weapons or shields.
- Nothing is installed into the game. Engine version remains 0.4.0-pre; no executable change accompanies this model.

## Rebuild without game artwork

Requires Blender 5.1 (validated with 5.1.2). Run from repository root, substituting your Blender executable:

```powershell
& $blender --background --factory-startup --python-exit-code 1 --python tools/warrior3d/build_warrior.py -- --calibration tools/warrior3d/calibration/light-unarmed.json --out ../warrior-output --render all
& $blender --background ../warrior-output/Warrior-Light-Unarmed.blend --python-exit-code 1 --python tools/warrior3d/validate_blend.py -- ../warrior-output/rig-validation.json
python tools/warrior3d/assemble.py --model ../warrior-output
```

Assembly requires Pillow. Output includes exact-grid PNG sheets, eight-direction contact image, and idle/walk GIFs. GIF timing is an offline preview, not the game's animation timing. The saved scene is authoritative; generated outputs stay outside the repository.

## Optional local reference fitting

`prepare_reference.py --nn-root <DIADAT_DH_NN_8x> --original-root <extracted-DIABDAT> --out <private-reference-dir>` measures the Warrior idle/walk layouts and decodes original CL2 body silhouettes, excluding palette index 0 ground shadows. Then pass `--reference <private-reference-dir>/reference.json` instead of `--calibration` to the builder. Assembly accepts `--reference <private-reference-dir>/reference.json` for silhouette diagnostics; see its help for arguments.

Reference PNGs, CL2s, decoded masks and comparison overlays remain local and must never be committed. The tracked scene contains generated geometry/materials and no image textures or packed game artwork. Numeric camera/root calibration contains no sheet pixels. `compare_silhouettes.py` creates private diagnostic overlays only.

Next art milestone: refine one idle pose in all eight views before expanding equipment or producing all Warrior sheets. Preserve original action frame counts, direction order and foot anchors during refinement; test a separately backed-up in-game sheet override only after visual acceptance.

Direction contract (confirmed by the user): columns 1-8 are South/Down, South West/Down Left, West/Left, North West/Up Left, North/Up, North East/Up Right, East/Right, South East/Down Right. Rows advance the animation from top to bottom. South uses model yaw 0 degrees; each next column subtracts 45 degrees. Do not infer facing from silhouette aspect ratios.

The light-armor model uses one pauldron on the Warrior's left shoulder (viewer-right in the South-facing view), as corrected against the local reference. Both forearm bracers remain.
