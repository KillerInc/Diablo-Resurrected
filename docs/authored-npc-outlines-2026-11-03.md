# Authored NPC hover outlines â€” 0.4.21-pre

Hovering an authored town NPC previously outlined the original CEL, even though
the replacement used its own BC7 silhouette and anchor. The resulting outline
could float beside the character or cross its body.

Authored towners now queue an ordered GPU outline using the selected HD frame.
The outline expands one logical pixel around alpha of at least 0.8, excluding
the authored 70% ground shadows. Sampling is bounded to that frame's packed
rectangle, including when the outline extends beyond the crop or atlas edge.
The normal palette supplies the selection colour; existing foreground coverage
and cursor restoration remain active. No extra image, CPU decode, animation
frame, asset-index change or persistent per-NPC outline texture is required.

Classic, unmarked world art, UI outlines and virtual-gamepad fallback retain
their previous outline paths.

Validation includes GPU pixel readback for the exterior outline, transparent
interior, translucent shadow rejection, packed-frame bounds, foreground
occlusion and cursor restoration. The existing synthetic lighting, translation,
native-index, actor-ordering and resource-release checks remain in the same test.
Private gameplay/UI replay results and installed-pack checks are kept outside Git;
no game artwork, saves or captures are included here.

## Shadow ordering, 0.4.22-pre

Hovered authored towners now queue their sprite first and their outline second,
so their baked shadow cannot darken the selection edge. The pair retains the
original actor position in scene traversal; later foreground coverage and cursor
restoration still apply. Classic and unmarked towners keep their original path.
GPU readback also checks exact outline colour over a translucent shadow.
