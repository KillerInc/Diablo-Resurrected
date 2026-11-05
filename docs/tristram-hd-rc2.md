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
