### Diablo Reincarnated research backlog

- Investigate renderer multithreading after the current HD artwork pass: visible
  terrain preparation, independent lighting regions and GPU command-data
  preparation. Preserve ordered composition, snapshot shared simulation data and
  keep final GPU submission coordinated. Measure worker/merge overhead against
  the warmed single-thread baseline before enabling any path.
- Expand scene coverage of the installed HD dungeon objects, town NPCs and
  special level overlays to remaining quest/object animations; preserve native
  palette indices, frame IDs and anchors when replacing artwork.
- Continue 3D monster candidates alongside world integration. Recheck animation
  exports and rig compatibility before treating any imported model as animated.

### Comments

- `BUGFIX` known bugs in original (vanilla) code
- `/* */` block comments are things to be fixed/checked
- `FIX_ME` bad data

Code issues (incorrect code that still works)

- Critical sections should be constructors using `CCritSect`
- Some functions/structures have incorrect signing (signed/unsigned BYTE)
