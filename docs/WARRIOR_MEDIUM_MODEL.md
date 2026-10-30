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
reviewed in the static pose from front, rear and oblique angles. Animated
clearance is still pending; no medium sheets have been installed in the game.
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

## Approved base selection — 2026-10-29

The user approved `D1 Warrior Medium - blue gray.glb` as the Medium Warrior
base. `tools/warrior3d/medium_warrior_source.json` records its identity and
appearance choices; use this approved revision for medium animation/sheet
work, retaining the fitted straps, blue mail/outfit, darker helmet and gold
accents. Keep cape/skirt disabled. The original GLB and earlier variants are
preserved. Approval selects the model; animated clearance and medium sheet
replacement remain pending, and the installed game is unchanged.
