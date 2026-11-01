# NPC and object HD integration, 0.4.18-pre

The private prepared pack adds 70 dungeon-object resources, 14 town NPC
resources and three special level overlays to the terrain/UI/player pack.
The merged index has 1,387 sheets, 3,061 BC7 pages and 9,742,352,384 texture
bytes. These are existing game artwork enlarged to four times each dimension,
not newly modeled NPCs or invented detail. Artwork remains local.

The prepared RGB sheets share the original town palette. Looking up their RGB
against the current dungeon palette would select incorrect indices; duplicate
palette colours also make RGB inversion ambiguous. The renderer therefore
caches exact native CLX index and occupancy for each frame in a small GPU
texture. The shader uses those indices for current-level lighting/translation,
including opaque index zero. Native indices are keyed by compressed content,
dimensions and translation identity, not temporary sprite addresses. Existing
monster/player/missile materials retain their previous lookup path. Missing
compiled resources or source palette retain Classic rendering.

PNG viewing copies may accompany BC7 pages, but runtime loading remains BC7
only. `install_world_pack.py --preview-hd ...` adds matching previews and
refuses to overwrite unknown BC7 pages, PNGs or existing index records.
Only the combined root index is replaced, after backup and validation.
The layout CSV and original player sheets are preserved.

Validation includes synthetic duplicate-colour/opaque-zero GPU readback,
the existing sprite/UI/terrain/provider/mode tests, every compiled page through
the real GPU loader, repeated copied-save outcomes and UI/F10 regressions.
Muted private debug replays use a recorded level-transition event: live SDL
events posted by a debug warp are intentionally discarded during replay.
Town checks visit NPCs after loading. `D1R_TRACE_WORLD_SHEETS=1` reports
successful world draw submissions separately from sheet residency.

3D monster work is separate from these native NPC/object sheets. The current
22 Baddies GLBs contain no embedded animation clips. A skeleton donor-motion
experiment preserves source geometry/materials and retargets shared humanoid
bones; it is not an approved native monster animation or an installed pack.
The melee goatman export contains only one skin joint and needs re-exporting
with its full rig before articulated motion can be assessed. Original monster
animation exports are still required for an authentic-motion comparison.

Renderer multithreading research is tracked in `docs/TODO.md`; this release
does not change simulation or make graphics work concurrent.

## Local validation results

Release SHA256: `D0F465F30F20E1BDDB1D3A658E72D832092252DF4EB1C69BAEEB996B8BE1B49E`.
Debug SHA256: `B57D43A654717991A9B9BD3D8125BD702D0BD9C876BB038E4D4FBC6F2FD8494F`.
Combined index SHA256: `763BE7A63805BE493B5A4D2D8575A14BE5B670F6688AD48B6C896212BDF0F0C0`.

Both repeated save replays produced the expected final outcome. The release
UI replay toggled Classic/HD and the performance overlay successfully.
The steady release HD replay retained all 255 Warrior sheets; its last ten
intervals recorded zero CPU sprite decodes and unchanged page-upload counts.
The entire 1,387-sheet compiled pack passed real GPU upload validation.
Town draw traces confirmed Cain, Griswold, Pepin, Ogden, Farnham and the town
overlay; dungeon traces confirmed special overlays, doors, braziers, barrels,
chests and sarcophagi. Representative town/dungeon captures were reviewed
privately. This is sampled scene coverage, not a claim that every possible
object/quest animation was visited. Synthetic sprite/UI/terrain/provider/mode
tests and installer preservation/rejection tests passed.
