# Approved Medium Warrior model

The user-authored medium Warrior export intentionally excludes its cape and skirt.
Keep the cape_sim and skirt_sim objects hidden; their untextured materials are
not missing-texture defects to repair. Preserve the belt, mail and armor plates.

The detached neck/back cords and shoulder fasteners are fitted against the mail
and shoulder armor. Smooth surface displacement bends cords while retaining
braid thickness. Engraved disks move rigidly, using front/back projection for the
shoulder clasps. Do not project the small shoulder plate components as if they
were straps. Preserve non-trim positions, topology, UVs, materials and skin weights.

The Blender tools accept private prepared scene paths and a component audit:

```
blender --background --python tools/warrior3d/audit_medium_warrior_straps.py -- SCENE.blend COMPONENTS.json
blender --background --python tools/warrior3d/fit_medium_warrior_straps.py -- SCENE.blend COMPONENTS.json NEW_OUTPUT_DIRECTORY
```

The recipe targets the audited 7,443-vertex torso and 633 skin groups. Component
identifiers are specific to that topology; re-audit after geometry changes. The
input scene is preserved and output must use a new folder. The fitting pass is
reviewed in the static pose from front, rear and oblique angles. Animation and sheet validation are recorded in the production result below.
Models, textures, private reports and renders remain outside Git. No executable
change or build-version bump is required for this model-only working pass.

## Blue and gray material pass

`tint_medium_warrior.py` takes the same private prepared scene/component audit
and a new output directory. It gives the central chest mail and lower outfit a
muted blue cast inspired by vanilla, while keeping the waist medallion and
shoulder plates in their existing gray metal. The helmet's neutral metal is
darkened to match the armor, protecting warm gold accents. The texture pass
preserves warm leather/rust detail and alpha. Geometry, UVs and skin weights
are hashed before/after and must match. The prior strap fit and disabled cape
and skirt are retained. Original models/textures are preserved; only a new
private GLB/Blender copy and review renders are written. Review the exported
material assignment and front/oblique views before use in animation sheets.

## Approved base selection â€” 2026-10-29

The user approved `D1 Warrior Medium - blue gray.glb` as the Medium Warrior
base. `tools/warrior3d/medium_warrior_source.json` records its identity and
appearance choices; use this approved revision for medium animation/sheet
work, retaining the fitted straps, blue mail/outfit, darker helmet and gold
accents. Keep cape/skirt disabled. The original GLB and earlier variants are
preserved. The initial approval selects the model; the subsequent animation and sheet
validation is recorded below.

## Animation and sheet pipeline

`prepare_medium_warrior.py` transfers the audited light-motion catalog onto the
approved medium base, checking animated rest matrices and parents. The approved
short town stride, full attacks, centered weapon grips, shield bash, town stows,
bow quiver and spell effects remain the donors. Medium-specific native row
counts are sampled over each complete motion; no limb attenuation is used.

`preflight_medium_warrior.py` checks all poses and expands transparent canvases
for the armor, equipment and full southeast shadow. The raw capture camera
scales with its transparent canvas, retaining constant world pixel density.
`audit_medium_equipment.py` checks actual head/helmet intersections across all
66 equipped-sheet pose sequences. The native stowed axe needed a 4 cm shift in
chest-local X for the new helmet; the same translation applies to town idle and
walk. `fit_medium_town_axe.py` preserves character motion and weapon rotation.

`render_medium_warrior.py` resumes completed work, reuses identical captures,
and uses ordinary copies where Windows denies hard links. Sources retain NN8
canvas density and the approved Diablo grading; body and equipment shadows
project from the southeast sun. Explicit anatomy tokens include the medium
helmet and outfit instead of assuming the old six-part light mesh.

`compile_medium_warrior.py` prepares per-frame native-4x inputs and BC7 pages
as renders complete. The final pack preserves the 170 light/heavy sources and
rebuilds the single `sprites.gpus` plus `layouts.csv`. If a completed sheet is
corrected, finish the main batch and use `refresh_medium_sheets.py` explicitly
before validation; this backs up and recompiles those records. The town-axe
correction uses this path. Compression validation samples every custom sheet
present, rather than assuming only the original 85 light replacements.

`install_medium_warrior.py` requires render review, real GPU/replay proof and
an isolated medium-look test. It verifies the original installed data before
replacing 85 medium PNGs and GPU records, backs up all overwritten/obsolete
files, and rolls back on failure. Light/heavy data, the executable and user
saves/settings are preserved. Synthetic tests exercise success and rollback
after old GPU pages have been retired. Runtime metadata remains root-only.

`prepare_medium_live_test.py` creates a private visual test pack that maps the
fixture's nine compatible light sword/shield lookups to verified medium pages without changing the
save's equipment or statistics. This tests the actual medium image payload in
the existing GPU renderer; normal reference replays separately test the real
pack. All test audio uses the existing half-volume override.

`archive_medium_warrior.py` preserves the approved base, exact compact skeletal
donors, gear, references, review GIFs and validated runtime GPU data privately.
`extract_approved_motion.py` retains sampler data and rest nodes while omitting
redundant donor meshes/textures; raw motion remains private too. No new engine
or executable build is needed for this artwork revision.

## Installed production result — 2026-10-30

Medium graphics revision `medium-v1` installs all 85 medium sheets, covering
9,408 directional body/shadow frames. All 41 motion donors match the medium
skeleton exactly; all 66 equipped pose sequences pass head/helmet clearance
following the 4 cm town-axe adjustment. Original light/heavy assets and the
approved short walk stride are preserved. The cloak and skirt remain off.

All 255 Warrior GPU sheets decode and validate across 804 BC7 pages totaling
2.488 GiB. Compression checks cover all 170 custom light/medium sources; worst
sampled visible RGB RMSE is 2.4358 and alpha RMSE 2.2727 on the 0–255 scale.
Two reference-save replays match, F10/F11/UI checks pass, and the medium image
payload is reviewed in the existing GPU renderer using the isolated visual
pack. The selected class remains GPU-resident with zero retained CPU player
RGBA and no warm page uploads. Test audio remains at half volume only for tests.

The existing 0.4.7-pre executable is unchanged. `HD/layouts.csv` now contains
170 custom rows; `HD/sprites.gpus` remains the only runtime compiled index.
The graphics installer backs up prior medium PNGs/pages and tables, and a
private assets archive preserves the approved base, exact motion donors,
references, equipment, review GIFs and the complete runtime GPU pack. No
proprietary artwork, models, raw motion or captures are included in Git.

## Equipped casting revision — 2026-10-30

`equipped-casts-v1` replaces the 24 equipped medium FM/LM/QM sheets and the
corresponding 24 light sheets with approved native Aura Fanaticism motion.
Weapons/shields remain held; unarmed casts and all other actions are preserved.
The body model, cape/skirt visibility, colors, short walk and town equipment
remain unchanged. The `medium-v1` figures above describe that earlier installed
revision; the current class has 867 pages totaling 2.726 GiB. See
[the equipped casting record](WARRIOR_EQUIPPED_CASTING.md) for the current
render, grip-clearance, runtime and installation proofs.
