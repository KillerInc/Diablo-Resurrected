# Segmented Warrior weight repair

Run Blender 5.1 against the user's local 39-part `D1+Warror+GLB+Segmented.glb`:

```powershell
& $blender --background --factory-startup --python-exit-code 1 --python tools/warrior3d/segmented/repair_weights.py -- --input '<local-model.glb>' --out '<private-output-directory>'
```

The script preserves imported joint locations and rest geometry. It binds inspected rigid gear to individual bones and removes unrelated influences from body/clothing pieces, renormalizing remaining weights. It saves an editable Blender candidate, GLB copy, before/after renders and a numeric report. Sword and back shield pieces are retained in a reversible optional collection, hidden for the Blender unarmed preview. The GLB copy retains equipment for compatibility; use the Blender scene for the explicit hidden-equipment state.

Validated on the supplied export: 39 character meshes, no source animations. A repeatable 65-degree shoulder, 25-degree elbow and 20-degree knee test reduced mesh edges stretched more than 3x from 183 to 0. Maximum edge stretch fell from 12.08x to 2.005x. This measures stretching only: it does not establish joint closure, collision freedom, anatomical correctness, or animation readiness.

**Remaining work:** open shoulder boundaries are exposed in raised-arm poses; hands retain the original weapon-gripping pose; equipment remains in its original rest locations; knee/boot joins need additional inspection; the segmented textures are lower resolution than the original 4K source. No new idle/walk animation or game-sheet replacement is approved. A simple shoulder seam weight blend was rejected because it introduced worse stretching; shoulder surface reconstruction or deliberate topology/weight repair is still needed.

All third-party geometry, textures, Blender outputs and rendered diagnostics stay local outside the repository. Only this repair script and documentation are tracked. Nothing modifies the original exports or installed game files. The part map is specific to this inspected export, not a general Tripo model repair tool.
