# NPC shadows use the player projection

The player's fixed sprite camera projects opaque geometry onto the ground with
sun `(3,-4,6)`. NPC cameras may rotate to preserve an approved facing. Applying
the same world-space ray to those rotated cameras changes the on-screen sun:
Pepin and Ogden were conspicuous examples. The ground ray must instead follow
the camera's horizontal right/forward basis, keeping the sun southeast on screen.

`tools/warrior3d/render_npc_shadows.py` accepts a private recipe containing the
approved source scene, camera fit and exact native-frame samples. It renders
only projected shadows, excluding alpha hair cards, face overlays and effects.
`assemble_npc_shadows.py` composites them beneath existing body renders with
fixed registration. It rejects changed opaque body pixels and clipped cells.

Use 70% shadow opacity. The player's two-pixel blur at authoring density 8
corresponds to one pixel at the NPCs' density 4. Do not reapply body brightness
or saturation adjustments. Preserve native frame counts, sequence and timing,
logical dimensions, anchors and the cached root layout table.

The private nine-NPC correction covers 160 native frames. All opaque body pixels
match the installed approved art; body and shadow bounds fit every cell. BC7
output must pass the runtime pack upload test before installation. Install new
hashed page names, retain unrelated index records, back up replaced PNGs/index,
and publish the index last. Keep artwork, recipes with private source paths,
compiled pages and comparison captures outside Git. No executable change is
needed; the game must restart to read the updated cached index.
