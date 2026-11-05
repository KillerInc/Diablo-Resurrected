# Tristram HD RC2

HD RC1 is the installed HD art and existing game executable at the end of the
localized player house repair. Keep its private backup separate from RC2 work.
The private snapshot contains the HD directory, executable, and project MPQ.
It uses the owner's existing Diablo data archives.

RC2 separates artwork by object and location while retaining native simulation.
An artist can work on a whole house as one image. Export its visible pieces to
an atlas, with a binding for each original `(x, z, block)` draw slot. A binding
must also check the native piece or frame before substituting its image. This
keeps each building independent and lets quest states select the correct art.

| Art layer | Content | Drawing rule |
| --- | --- | --- |
| Low ground | Grass, dirt, rivers, terrain at tree bases | Draw continuous terrain with the native floor pass. |
| High ground | Rock bases, bridge decks, fence and house bases | Draw flat surfaces beneath actors where appropriate. Keep raised or overlapping parts in their native depth slots. |
| Actors | Player and NPCs | Use native traversal, movement offsets, and depth rules. |
| High | Roofs, walls, cathedral and house structures | Draw fragments at their native depth slots, interleaved with actors. |

These layers organize the art. In the renderer, a structure can appear in front
of an actor on one side and behind the actor on the other. Preserve this by
keeping per-cell draw order, anchors and occlusion. Retain delayed tree leaf
ordering if tree art is moved into the same texture atlas. Walkability, object
interaction, entrances and quest state come from the original game data.

Rocks are props over a complete ground surface. Remove all baked grass and dirt
from the prop's alpha silhouette. Place shadows separately beneath the prop.
Use the same separation for tree roots and fence bases where terrain is baked
into their current art. Keep native gameplay collision independent of alpha.

## Implementation steps

1. Establish instance-specific bindings in an offline preview. The cabin proof
   copies selected roof fragments into independent draw slots. It compares both
   assembled houses with the originals, then recolors only the east cabin's
   bound slots and verifies that the west cabin stays pixel-identical.
2. Author one patch of continuous ground and a transparent rock prop. Preview
   them assembled at their real location and check both sides of the rock.
3. Wire one cabin into the existing HD renderer behind an RC2 opt-in. Keep the
   native draw slots and validate movement in front of and behind the cabin,
   walking around the rock, bridge edges, and both states of changed entrances
   and fountain tiles before expanding across Tristram.

The first proof is offline. It does not change the executable or install art.

The riverside rock proof exports three private images at the same projection
and origin. The reconstructed grass and dirt are fully opaque. The rock keeps
its RC1 pixels inside an authored silhouette and has transparent surroundings.
Its contact shadow has a separate alpha mask. The comparison shows RC1, clean
ground alone, and the three layers assembled. The native slot audit records
which cell/block positions contributed to the rock silhouette. Several of the
rock pixels come from blocks 0 and 1, so block number alone cannot distinguish
ground from a prop. Use the native floor and cell rendering rules when adding
runtime bindings. Walkability and actor occlusion still need an in-game test.

The isolated runtime proof uses `D1R_HD_RC2_ROCK_TEST=1` and a separate BC7
terrain sheet named `town-rc2-rock.png` in the HD index. The authoring tool
`pack_instance_preview.py` appends 11 replacement frames, leaving all original
atlas slots intact. The test binds each replacement by world cell, native piece
and native frame. It draws the authored composite in the existing native depth
slots. The ground, shadow and rock are separate authoring layers in this proof.
Independent GPU drawing of all three layers remains a later step.

For an isolated demo capture, set `D1R_HD_RC2_ROCK_CAMERA=1` to frame the river
patch. This camera setting only applies during town replay and does not move
the player. The river restricts movement around this particular rock, so use a
different, reachable prop for the full front-and-behind walk test.

The walk test uses `D1R_HD_RC2_ROCK_TEST=2` and a reachable copy at `(76, 77)`,
south of the player house. It draws the reconstructed ground in the floor
pass, queues the shadow after the floor, and queues the transparent rock at
the solid cell's normal content position. The prop and shadow use separate
frames of the same BC7 sheet. The native solid flag and actor traversal still
control movement and depth. The replacement ground atlas has 14 instance
bindings covering the rock and its immediate surroundings.

`D1R_HD_RC2_WALK_REPLAY` places a fresh isolated demo hero at `(76, 76)`.
The identical click input with RC1 and RC2 produced the same route through
`(75, 76)`, `(75, 77)`, and `(75, 78)` to `(76, 78)`, bypassing the solid
center cell. Both muted runs exited normally, and the RC2 GPU captures show
the hero on each side. The rebuilt GPU terrain regression test and BC7 pack
upload also passed. The installed RC1 executable, index and town atlas match
the frozen snapshot. This verifies one rock in the test build.

The riverside house runtime test uses `D1R_HD_RC2_HOUSE_TEST=1`. The
`clone_town_instances.py` tool appends 76 private house frames to the test
atlas and writes a versioned binding file. The loader selects replacements
only when the world cell, native piece and original frame agree. This lets
the east house use its own artwork while the west cabin keeps the shared
frames. Each private frame still draws at the original native depth slot.

All 3,584 original BC7 frames and 76 private copies decode pixel for pixel
to their RC1 originals. Two isolated replays used the same click input,
starting at `(69, 68)` behind the house and finishing at `(75, 68)` beside
its front door. Both took the same 11 moves around the house. The captures
show the roof covering the hero from behind and the hero visible at the
door. This test is private and opt-in. The installed RC1 files still match
the frozen snapshot.

Enable both `D1R_HD_RC2_HOUSE_TEST=1` and `D1R_HD_RC2_ROCK_TEST=2` for the
combined test. `merge_town_instances.py` builds one terrain atlas and one
binding table from the two proofs, with 76 house slots and 14 rock ground
slots. The rock and shadow still use separate prop frames. The merged frames
decode exactly like the verified individual packs. One muted replay walked
around the house, continued south to the rock, and walked around its blocked
center to `(76, 78)`. The replay exited normally. This pack stays isolated
from the RC1 installation.

The west cabin adds 58 private roof and wall frames, for 148 total bindings
with the riverside house and layered rock. The merge tool carries these over
two private columns while retaining all 3,584 native frames. It rejects
overlapping binding keys and inputs with different base artwork. The west
cabin frames decode exactly like RC1. The earlier house and rock frames and
the transparent prop sheet also match their previous verified packs.
RC1 and RC2 replays took the same 11 moves from `(25, 50)` behind the west
cabin to `(31, 50)` beside its front door. The RC2 log recorded a private
west cabin frame, and both replays exited normally.
