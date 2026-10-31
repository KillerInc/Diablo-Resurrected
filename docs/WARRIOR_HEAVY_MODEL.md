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
