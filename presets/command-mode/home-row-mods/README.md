# Home-row modifier preset

`home-row-mods16.vil` restores your base hold modifiers, Tab keys and Shift positions on the everyday layers. Load it into the already-installed Corne v4.1 standard command-mode firmware. No new flash is required. Firmware, the Mac helper, the private protocol and the registry hash remain unchanged.

This optional follow-up starts from the verified `baseline16.vil`, SHA256 `34c9215bfecb4149c21ac5300639ea38abd2f3ec6110a81294824a3d6df5b3d0`. It does not start from a fresh device export. Your existing Mouse, Auto Command app selection and Home checks establish that the installed setup works. This new preset has not been imported or physically tested.

The exact 115 changed matrix cells are in [changes.json](changes.json). [manifest.json](manifest.json) records the source and candidate hashes. [SHA256SUMS](SHA256SUMS) covers these assets. The original baseline16 and experimental16 presets remain historical options.

## Controls

The covered layers are Typing 0, Numbers 1, Symbols 2, Generic 6, OpenAI 7, Claude 8, Browser 9, Editor 10, Review 12 and Experiments 13. Typing 0 already has the correct mappings and stays identical.

| Base key position | Hold on each covered layer | Tap on the command panels |
|---|---|---|
| Left A, matrix1,1 | Left Command | Left arrow |
| Left S, matrix1,2 | Left Control | Down arrow |
| Left D, matrix1,3 | Left Option | Up arrow |
| Left F, matrix1,4 | Left Command | Right arrow |
| Right semicolon, matrix5,1 | Right Command | Left arrow |
| Right L, matrix5,2 | Left Control | Down arrow |
| Right K, matrix5,3 | Right Option | Up arrow |
| Right J, matrix5,4 | Right Command | Right arrow |

Numbers and Symbols retain their existing home-row tap keys. Blank tap positions become plain held modifiers with no character or one-shot state. Every nonblank home-row tap uses its original basic keycode.

Both left Tab positions, matrix 1,0 and 1,6, are real Tab. Physical left Shift at 2,0 and right Shift at 5,6 return to their base roles. Command panels also have left Shift at 6,0, the mirrored destination of 2,0. Hold a home-row Command key past the existing 200 ms tapping term, then press your usual Tab for Command-Tab. Add a physical Shift for Shift-Command-Tab. A fast roll that releases the home-row key before 200 ms remains a tap, as on your base layer. Quick-tap timing and all other tap/hold settings stay unchanged.

OpenAI 7 now places explicit F18 on the left bracket auxiliary key, matrix 0,6. Claude 8 places the guarded Control-Option-Shift-D Raycast dictation chord there. Each action has one logical binding. Under Mirror, the right bracket auxiliary key at 4,6 reaches that binding. Logical 4,6 remains unused.

The left Backspace thumb at 3,4 stays unused in these panels because Mirror swaps it with the protected right FN thumb at 7,4. Placing voice there would make mirrored FN invoke voice. Both old voice positions, 2,0 and 6,0, become Shift. Normal and mirrored Shift and FN cannot invoke voice. No voice shortcut was executed during this change.

Mouse 11, Picker 15, Maintenance 3 and reserved 4,5,14 stay identical. Menu, Home, FN, right Command thumb, Mirror controls, normal Space, encoders, macros and every other saved field stay identical. Mirror follows logical positions. A mirrored right-hand home-row key uses the opposite side's hold family, as defined by the hand-swap map.

## Generate and check

Run these commands from the repository root:

```sh
python3 tools/home_row_mods_preset.py generate
python3 tools/home_row_mods_preset.py check
python3 tests/home_row_mods_assets.py
```

Generation accepts only the exact verified source bytes. The transform derives hold families from base0 and rejects unrepresentable home-row tap codes. It emits a new preset, the complete before/after diff and hashes. It never rewrites the old presets or firmware assets.

Follow [the manual loading guide](../../../docs/home-row-mods.md) before importing. Export your current device state first. The read-only comparison must report a match before you use this preset.
