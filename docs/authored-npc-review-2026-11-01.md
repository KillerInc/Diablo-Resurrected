> Superseded for normal installation by [0.4.20-pre](releases/0.4.20-pre.md).
> The review switch below describes the earlier 0.4.19 trial.

# Authored NPC review build, 0.4.19-pre

`D1R_TEST_AUTHORED_TOWNERS=1` allows a compiled town NPC with an explicit
root-layout CSV row to use its own rendered silhouette. Native NPCs without
that row retain exact native index/occupancy textures. The option is for private
art review, remains off by default, and does not add PNG runtime loading.

Frame counts must still exactly match native CEL metadata, with or without
the review option. The native CLX frame selects the BC7 frame; there is no
independent animation clock. Frame order, delays and gameplay remain unchanged.
Synthetic GPU validation checks both rejection of mismatched counts and opt-in
selection of matching authored NPC sheets, alongside existing lighting,
translation, blending, native-index and resource-lifetime readback tests.

The private Griswold trial samples a longer Blender source into the original
16 frames: frame 0 is arms-down rest; 1-3 cross; 4-13 are the repeating crossed
idle; 14-15 uncross. The original towner table and its animation-order list
are unchanged. The BC7 sheet is 4x dimensions with a registered foot anchor
and southeast shadow. Its model, textures, sheets, saves and captures remain
local and must not be committed.

A muted isolated normal-speed replay on the left display confirms an actual
`HD_WORLD_DRAW` for `hd/towners/smith/smithn.png`, `native_indices=0 frames=16`.
Other town NPCs retain `native_indices=1`. The trial pack overrides only the
smith sheet record and adds its CSV row; installed game files are unchanged.
This is a debug artwork review, not a performance benchmark or installed
release. A future production integration needs explicit authored-material
metadata rather than relying on this test environment option.
