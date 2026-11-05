# Copy-only storage save tool

`reincarnated_save_storage_tool` is an optional SDL3 build target. It links the
existing engine archive reader/writer and save checksum codec; it does not modify
or replace the game executable. Save files and private receipts never belong in Git.

Commands:

- `inspect PROFILE`: identify single-player character files and shared storage gold.
- `quarter-copy INPUT OUTPUT`: create a new archive copy with single-player stash
  gold set to floor(INT32_MAX / 4), or 536,870,911. The input is never written.
- `verify INPUT OUTPUT`: verify the desired gold, identical decoded stash bytes
  outside the four-byte gold field, archive member count and every other member.

The stash lives in a shared `stash.sv`, with `spstashitems` for single-player and a
separate `mpstashitems` member for multiplayer. Storage gold is an `int`, with
addition guards at INT32_MAX; its serialized field is uint32. This is separate
from inventory gold and the per-pile gold limit.

This tool supports the current Diablo stash version 0 and 2048-slot MPQ save
archives. Unsupported formats are rejected. It preserves raw non-target archive
members through the engine writer and verifies decoded item/page bytes exactly.
It does not reserialize items or character records. Always prepare a new working
copy, retain an exact original backup, verify the result, and install atomically
only if the source has not changed since the snapshot.

A running game holds stash contents in memory and may overwrite external edits.
Prefer closing it first. If the user explicitly chooses a live on-disk edit,
explain that risk and do not claim to have changed the running game's memory.
The helper never attaches to or patches another process.
