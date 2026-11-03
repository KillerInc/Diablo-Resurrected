# Tristram scene reconstruction and town atlas contract

The initial authoring scene reconstructs the supplied Tristram buildings and a
native-grid ground/scenery cache in Blender. It is a review candidate, not a
verified one-to-one replacement. The installed executable and graphics pack are
unchanged. No proprietary or supplied artwork belongs in this repository.

## Inputs and provenance

The format and projection adaptation is based on Douglas Pan's
[Diablo3D source](https://github.com/douglasopan/diablo-3d), inspected at main
commit `1e0fcf3855a566a32b15391402fc0b4f3652eb60`. Its software is distributed
under the [Sustainable Use License](https://github.com/douglasopan/diablo-3d/blob/main/LICENSE.md),
also inherited by this project. This authoring conversion is a modification,
not an upstream tool or an asset-rights grant. Preserve upstream notices.

The private input package is the `local6-tristram.grid162` Windows release,
SHA-256 `703a684625ff155ba7ce08d2a3a31f99f40028142ac37aa6a132d89c0b0f2639`.
The headless preparation helper was checked against its release manifest and
reviewed source, then used only to read the user's original retail MPQ and
write a new isolated cache. No game, audio, preferences or save manipulation is
needed. The resulting static cache matches the package's frozen baseline hash
`d463e0dee0f022f7b5ecbf9912a787215fa8608fcab7077fbf8cf2fc591198ff`.

Selected architecture uses the package's final fourteen prefabs and saved
placement transforms. The static cache retains native coordinates; the later
static byte edits and WorldPatch are not applied. No 1.62 gameplay world-scale
enlargement, collision change or routing change is imported into our game.
The upstream final building transforms can still differ from vanilla, and need
per-building comparison before claiming exact placement or silhouettes.

## Reproduction

1. Prepare a private `D3DSTAT1` cache plus `palette.rgb` using the verified
   upstream helper and the user's retail data. Keep that extraction private.
2. Read the original `town.min` and `town.sol` using the existing read-only MPQ
   extractor. Use the installed native-4x town PNG as a private source atlas.
3. Run `tools/town3d/convert_scene.py STATIC SCENE NATIVE ATLAS OUTPUT`.
   `SCENE` contains `d3d-scenes/tristram.ini` and its hashed final prefabs.
4. Run Blender in background mode with `tools/town3d/build_blender_scene.py`,
   passing the converted directory and an output directory after `--`.
5. Run `tools/town3d/test_convert_scene.py` for synthetic binary/coverage and
   projection checks. No original artwork is used by these tests.

The converted inputs retain all 25,743 static object records, source cells,
1,349 native indexed textures, 14 building groups and 3 embedded RGB textures.
Visible geometry is batched by native texture/kind/phase, with a separate
native-object map for source lookup. Buildings remain separate named groups,
with replaceable image materials and source hashes. Textures are packed in the
Blender scene and also retained as editable external PNGs.

The preview contains 1,286,587 triangles after exact alpha-zero ground geometry
is removed. Native floor rectangles overlap: leaving transparent coplanar
triangles in the scene caused missing-ground artifacts in both Cycles and
Eevee. The converter instead creates opaque coverage strips from the original
mask. This preserves native pixel coverage while making depth testing reliable.

## Camera and material rules

Original `(x,height,z)` maps to Blender `(x,-z,height*sqrt(2/3))`. A 30-degree
orthographic camera then reproduces native projected offsets exactly:

```
screen x = 32*(x-z)
screen y = 16*(x+z)-32*height
```

Synthetic points verify the conversion independently. The scene also contains
55-degree bird's-eye and 90-degree overhead cameras. Preview renders use unlit
palette textures; bird's-eye/overhead presentation has +1 exposure for review,
while the native-camera render remains at exposure zero. This is not production
lighting or a colour-grade approval. The initial scene excludes dynamic NPCs,
players, cursor, UI and gameplay objects that should remain separate at runtime.

## Remaining fidelity work

The supplied church, cabin and Pepin house contain embedded RGB. Several other
buildings have native projected fronts and provisional unseen surfaces. Those
faces, brightness differences, shape/scale/placement and silhouette coverage
must be reviewed against vanilla. Hidden interior/light adjuncts are recorded
but not imported. Some vegetation and scenery remains fixed sprite-ray relief,
not newly authored complete geometry. These are limitations of this candidate,
not a finished one-to-one town or permission to invent missing original art.

## BC7 production path

`inspect_town_atlas.py GAME_HD TOWN_MIN OUTPUT_JSON` records the installed atlas
and every native microtile use without modifying it. The current town resource
is `levels/towndata/town.png`: density 4, 28 columns, 128 rows, logical 32x32
cells (128x128 rendered pixels), stored across four BC7 pages. It contains
3,547 referenced source fragments and 37 padded slots; 65 source fragments are
shared by multiple MIN uses, across 1,258 native tile pieces.

After geometry/materials are matched, bake with the calibrated native camera
into the existing frame identities and alpha/foreground layers. A whole-town
beauty render cannot simply be cut into a new atlas: repeated source fragments
can acquire conflicting contextual pixels, shadows or shapes. Compare every
shared use, and report conflicts rather than silently overwriting one instance
with another. Conflicts may require a separate reviewed per-piece mapping in
the existing renderer, not a new engine. Do not pre-approve that change here.

Keep native floor/foliage order, bridge/wall occlusion, animation/quest variants,
logical anchors and source IDs. Encode a private candidate with the existing
BC7 packer; then validate loader/readback, native comparisons, gameplay and
index preservation before any installation. No production replacement BC7 is
generated or installed by this preview pipeline.

## Native registration and colour pass

`register_buildings.py CONVERTED NATIVE_INPUT TOWN_ATLAS OUTPUT` produces
native facade references and candidate ground-plane registrations. Tavern
main/wing and smithy house/forge are evaluated as pairs so their geometry is
not fitted independently to the same native artwork. Horizontal scale, height
scale and ground-plane translation are fitted against the original coverage
envelope. Height-zero vertices stay at zero; source UVs are preserved. Native
coverage includes fringe scenery, so this is not a proof of exact architecture.

The candidate is applied only when native coverage intersection-over-union
improves by more than 0.005 and the height scale stays within the review range.
The first pass accepts 12 models and retains the smithy pair unchanged because
its proposed adjustment reduces overlap. Example coverage scores:

| Group | Before | Candidate |
| --- | ---: | ---: |
| Cathedral | 0.484 | 0.736 |
| Well | 0.206 | 0.613 |
| Pepin's house | 0.706 | 0.921 |
| Tavern pair | 0.734 | 0.772 |
| Smithy pair, rejected | 0.744 | 0.737 |

Pass `--registrations OUTPUT/registrations.json` to `convert_scene.py` to build
a separate candidate. All 1,093 native static mesh batches remain bit-exact.
Registration does not modify the original prefabs, collision, logical tile
bindings or installed game. `render_building_comparisons.py` renders the groups
on the same native pixel canvas as their original facade references; it does
not resize each side independently to conceal registration differences.

The optional `--native-palette` creates separate albedo candidates for the
cathedral, Pepin's house and east cabin. Source UV coverage determines the
luminance distribution, which is matched to native facade quantiles and native
median colours. Original albedo PNGs remain unchanged. Texture dimensions and
detail order are retained; this is a reversible reference look, not approval
of every material, missing lit window or detailed shape. Native-camera renders
remain at exposure zero.

Six synthetic tests cover binary fields, truncated records, coplanar ground
coverage, camera calibration, ground-preserving registration, and reversible
palette matching. Private checks verify all 12 comparison canvas sizes, exact
static geometry/source UV preservation, untouched original albedos, and intact
installed town pages/index/layouts. The candidate still contains unfinished
roof/wall shapes, especially visible on the tavern, and requires further model
work before a one-to-one production bake. No BC7 replacement is installed.
