# Separate torso and trouser seams

Ogden and the wounded townsman had visible gaps where separately rigged torso
and trouser meshes met. Close the seam in the source geometry, rather than
covering it with a new belt or shifting the complete legs.

`tools/warrior3d/extend_npc_waist.py` raises only upper trouser vertices using a
smooth rest-space transition. Retain original UVs, materials, vertex weights,
rigs and animation. Ogden uses a transition beginning at rest-space z=0.85 and
0.12 lift; the wounded townsman uses z=1.02 and 0.13 lift. Units are the existing
source scene units. Source/output scenes and material tokens are supplied
privately on the command line; no artwork is included here.

The shadow renderer can optionally render repaired body cells using the same
camera fit and native-frame samples. Resolve output paths before opening the
Blender scene, since opening a scene can change Blender's working directory.
Keep the player-rule southeast shadows and the existing root layout anchors.

The private correction retains Ogden's 16 frames and the wounded townsman's
8 frames, including his still/dead frame. All 24 frames were reviewed at the
waist and checked for cell-edge clipping. Foot alpha and position match their
prior body renders exactly; slight lighting changes from the added geometry
are allowed. Validate the two BC7 sheets through the runtime GPU loader, retain
all unrelated root index records, and back up the previous PNGs/index before
installing. This is an asset correction; no executable or gameplay change is
needed. Restart the game to reload its cached sheet index.
