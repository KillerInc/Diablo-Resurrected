# Heavy warrior preparation

The user-supplied D1 Warrior Heavy.glb contains a rig and embedded textures.
The approved appearance replaces red with dark gray and gold/helmet with
metallic silver (metallic 0.95, roughness 0.28). Untextured cape/skirt/loin
panels are hidden. The hanging front tabard is removed as nine detached
components (633 vertices, 970 faces). A face/UV/skin-weight comparison confirms
all remaining leg geometry is unchanged; waist armor and leg plates remain.
The original model is preserved. No artwork, textures or animation data belongs
in Git.

Material exports must use fresh image datablocks: copying packed images can
retain the original packed red/gold bytes despite correct viewport pixels.
`bake_surface=True` stores the silver metallic/roughness mask in exportable
texture channels. The exported model was reimported and visually checked.

A private 85-sheet wh* plan uses 43 exact approved motion donors, retaining the
current equipment, short town stride, fire bubble v2, existing lightning and QM
effects. Every animated bone matches its donor rest matrix. Heavy native row
counts come from the installed GPU proof. Generic preparation now accepts
`--armor h --registry .../heavy_warrior_source.json`; medium remains the default.
Head audits recognize the heavy export's HLM material.

The heavy installer transaction and rollback passed their synthetic tests (ten
revision tests total). Heavy installation requires fresh bounds, head-clearance,
material-roundtrip, full GPU-pack, reference-replay and actual live-draw proofs.
The 170 light/medium source PNGs, GPU pages, index records and layouts must be
preserved. Graphics tests must mute all audio only in isolated configurations.

## Current state

Heavy sheets are not installed. The user requested black accents and asked to
compare all three options: undersuit/recesses, main plates, and both. Fresh
rotating previews use identical pose and lighting with front cloth removed.
Full production is on hold for that appearance selection. The installed medium
shield revision and light/medium artwork remain unchanged.

## Updated user model

The user supplied D1 Warrior Heavy black.glb in place of the generated recolor
options, then updated it again. The current tested source identity is recorded
in heavy_warrior_source.json. Its 15 meshes and supplied textures/materials are
preserved in an immutable private snapshot for testing. All 193 animated bones
match the approved idle donor; rest-matrix error remains below 0.000011.
The detached front cloth is removed using the same audited component pass.
No recolor pass is applied to this supplied model. No heavy sheets are installed.
The older generated-model production plan must be regenerated from this updated
source before rendering or installation; it is not the current body candidate.

## Approved build in progress

The user approved the updated black model and requested the full build. A fresh
production source preserves its supplied material data and removes only the
front cloth and previously disabled untextured panels. The 85-sheet plan retains
native heavy frame counts. Identical-byte motion models were canonicalized from
43 generated paths to 39 unique files; no motion data was changed.
All 85 bounds audits and 66 equipped head-clearance sequences passed. Shield bash
needed a further four-degree shield-only X rotation; arm motion is unchanged.
The full heavy sheets are rendering. Installation remains pending complete GPU,
replay and live-image validation; the 170 light/medium sheets must stay unchanged.

The parallel medium comparison tool produces 45 individual weapon-only animation
GIFs, five combined overviews and five eight-direction idle rotations. It reads
actual installed PNGs and the vanilla NN-x8 reference using the runtime index's
native row counts. Individual action comparisons show South. Generated media is
kept in the private T-Pose Images directory, never in Git.


## Installed black build, 2026-10-31

The approved supplied black body is now installed across all 85 heavy sheets.
The preceding pending/selection notes describe older stages. All 170 light and
medium PNGs, GPU pages, index records and layout rows were preserved. All 85
bounds checks and 66 equipped head-clearance sequences passed. Full body/shadow
cell validation, all-sheet visual review, two matching reference replays, UI,
preload/performance checks and a captured actual heavy GPU draw passed. The
installed-executable smoke replay also matched the reference save outcome.

The complete warrior class has 255 sheets, 921 pages and 3,112,509,440 BC7
texture bytes. There are zero CPU player PNG decodes and zero warm GPU uploads.
One root index and one layout CSV remain process-cached. Engine 0.4.7-pre,
normal user settings and saves were verified unchanged. All graphics tests
muted their isolated audio settings. Artwork and reproducible inputs are
private; Git contains source, tests and identity/validation metadata only.
