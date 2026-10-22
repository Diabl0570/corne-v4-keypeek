# App command trial

Import [app-trial16-vial075.vil](app-trial16-vial075.vil) only after refreshing or reconnecting Vial to reread the device and passing the fresh-export check in the [manual guide](../../../docs/app-command-trial.md). This is a separate trial for the existing command-mode firmware and helper. It needs no flash or helper change. No device import or physical Corne test has been performed for this trial.

`app-trial16.vil` is a non-import logical reference with exactly 121 changed cells against the verified `home-row-mods16.vil` source. Do not import that reference directly in stock Vial 0.7.5. Without custom key metadata, Vial registers only `USER00` through `USER15`; the existing Picker's `USER16` through `USER19` strings would silently decode as `KC_NO`.

The import file adds eight spelling changes on Picker15, using `0x7e10` through `0x7e13` for those same four keycode values on both halves. Every key keeps its meaning. The manifest lists these representation changes separately from the 121 behavior changes. Both files retain all non-layout fields, encoders, macros and timing settings. The other layers are unchanged, apart from those eight Picker spellings in the import file.

## Changed command keys

Layers 6, 7, 8, 9, 10 and 13 swap all five pairs at columns 1 through 5 between rows 0 and 2 and between rows 4 and 6. Undo, Cut, Copy and Paste move to the conventional left Z/X/C/V positions and the mirrored cluster. T/Y now return Home and disarm Auto. B/N now send Command-F for Find. Physical Menu double-tap remains the absolute Home fallback.

Only OpenAI7 changes the following keys after the swap:

| Keys | Matrix coordinates | Action |
| --- | --- | --- |
| Q / right P | 0,1 / 4,1 | Previous sidebar item, Option-Command-Left |
| W / right O | 0,2 / 4,2 | Next sidebar item, Option-Command-Right |
| Left bracket auxiliary | 0,6 | One-tap dictation, Option-Command-Space |

The paired auxiliary at 4,6 remains `KC_NO`. Mirror provides access through that physical side. Claude8 keeps `LCTL(LALT(LSFT(KC_D)))`. Home-row holds, Tab, Shift, Menu, FN, Mirror and Typing Space are preserved. Layers 0, 1, 2, 3, 4, 5, 11, 12 and 14 are byte-for-byte equal as JSON values in both variants. Canonical Picker15 is also literally unchanged.

## Verification and native evidence

The local tests use the original Vial GUI v0.7.5 codec at commit `e42622c352b69eff523a467718db487ab9c9cbf2`, with its pinned simpleeval dependency. They exercise every layout and encoder cell from both source and trial, prove the stock user-key import failure, and verify complete roundtrips with the eight safe spellings. No GUI, network or device is required at test or comparison runtime. The [fixture provenance](../../../tests/fixtures/vial075/README.md) identifies the original files and licenses.

The new comparison accepts only the exact export spellings demonstrated by this codec, including `KC_LCTRL`, `MEH(KC_D)`, the three new chord hex values, and the four Picker hex values. It ignores JSON formatting and object-key order. Every field and JSON value type still participates; changed settings, extra fields and wrong chords are drift. The separately named `legacy-source` result recognizes only the exact source with all eight affected Picker cells already lost to `KC_NO` and every other value unchanged modulo the observed spellings. Partial loss or any additional edit is drift. `KC_NO` is never an alias for a user key. If a fresh export matches that exact legacy profile, importing the safe file restores four duplicated selectors in eight cells as well as applying the intended 121 changes. No current keyboard state is assumed.

Native shortcut evidence was collected on `/Applications/ChatGPT.app`, bundle `com.openai.codex`, version 26.1016.61520, build 21421. Its existing one-tap Option-Command-Space dictation shortcut is enabled, and the human confirmed that the recording indicator appeared. Previous/next sidebar shortcuts were tested in both directions, including from composer focus. Navigation can leave HTML content focused; click your unsent draft before dictation. No preference change is needed. Speech transcription, a full dictation cycle and emission from the Corne still need manual testing. See the official [keyboard shortcuts](https://learn.chatgpt.com/docs/reference/commands#keyboard-shortcuts) and [voice dictation](https://learn.chatgpt.com/docs/prompting#use-voice-dictation) documentation.

Run from the repository root:

```sh
python3 tools/app_command_trial_preset.py check
python3 tests/app_command_trial_assets.py
python3 tests/vial_codec_roundtrip.py
```

[changes.json](changes.json) lists the exact sorted 121-cell reference diff. [manifest.json](manifest.json) records the source hash, both candidate hashes, upstream pins and eight representation changes. `SHA256SUMS` also covers this README. Use the saved fresh pre-import export for rollback, following the same guarded sequence in the manual guide. The old tools, presets and output packets are unchanged.
