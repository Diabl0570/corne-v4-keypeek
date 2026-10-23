# Corne command mode

This candidate adds sixteen layers, a physical Menu picker, momentary hand swapping and a native Mac app-context helper to the Corne v4.1 standard Vial target. Normal typing ignores app focus. Auto Command follows applications only after you select it on the keyboard; Home turns it off.

The current live configuration was exported and committed first, in [8fcbb76b](https://github.com/Diabl0570/corne-v4-keypeek/commit/8fcbb76b4e3af6429cd52f56df2ae92d1710c585). Its SHA256 is `eab35d0b53d2e56af2ca69d275762c0980122363a9fd53e82b733d795866c68b`. No candidate firmware or preset has been loaded onto the keyboard.

## Controls

The left outer thumb is Menu in every layer, including while mirrored.

- Tap Menu to toggle Numbers. A lone tap waits 200ms after release to distinguish it from a double tap. Pressing another key settles the single before that key is resolved. From a command panel, a single deliberately exits into Numbers.
- Hold Menu for 200ms to show Picker. Release without selecting to cancel. Choose a key while held to select its panel.
- Double-tap Menu to perform Home immediately on the second press. Home returns to typing, clears mirror and held layer overlays, cancels Picker, and disarms Auto.
- In Picker, left V selects Auto Command and left B performs Home. Esc selects Typing, Q Numbers, W Symbols, E Maintenance, A OpenAI desktop, S Claude, D Browser, F Editor, G Mouse, left Shift Review, Z Experiments, X Spare and C Picker. The generated legend lists every slot, including reserved layers4/5.
- The inner thumbs hold Mirror in command panels and Picker. Baseline typing Space remains Space. `experimental16` alone changes typing Space to tap Space / hold Mirror. Home cancels an experimental Space that is still held or queued, so it cannot emit a late Space after returning to typing.

[Open the physical key diagram](../presets/command-mode/legend.html) or [read the keycap legend](../presets/command-mode/legend.md). Both halves have duplicated command, mouse, scroll, button and speed clusters. The right middle thumb retains symbols; Numbers plus that thumb retains Maintenance.

App panels contain deliberate navigation/edit commands and `KC_NO` at unassigned positions. They stay selected until exit. A manually selected panel is pinned. Auto switches among Generic, OpenAI desktop, Claude, Browser and Editor. Raycast temporarily selects the existing Typing layer while Auto remains armed, then the next foreground app chooses its panel. Unknown applications select Generic only during Auto. The installed ChatGPT app identifies as `com.openai.codex`; there is one OpenAI desktop profile. Bundle IDs cannot distinguish Claude Chat from Code, browser tabs, or different views of the same app.

F18 and the guarded Claude Code Raycast dictation chord are explicit keyboard actions. The helper never invokes either. No voice, dictation, typing or submit action is part of app-focus observation or testing.

## Presets and upgrade

[`baseline16.vil`](../presets/command-mode/baseline16.vil) preserves every original matrix/encoder cell in the first six layers and every other saved field, then appends layers6–15. [`experimental16.vil`](../presets/command-mode/experimental16.vil) has exactly one additional change, `layout[0][3][5]`: `KC_SPACE` to `USER03`. [The generated difference and hashes](../presets/command-mode/manifest.json) make that change reviewable. Home-row tap/hold settings remain unchanged. Vial's `USER00` range is `QK_KB_0` at `0x7E00`; imported and compiled controls are checked numerically.

Sixteen layers move the EEPROM encoder/settings/Tap Dance/macro regions. Flashing this build does **not** preserve the six-layer EEPROM format. A checked, target-only early bootstrap initializes an incompatible image before settings are read. It seeds the captured personal keymaps and timing/mouse settings, preserves valid existing core/RGB preferences, and commits validity last. Core magic setting21 is preserved until the explicit full preset import. The source patch is pinned and hash checked; it does not upgrade Vial or KeyPeek.

At a later authorized physical flash session:

1. Keep the fresh six-layer `.vil` and prior working UF2 available for rollback.
2. Stop the helper and close KeyPeek before configuring in Vial. Flash the candidate appropriate for the user-confirmed v4.1 standard board to both halves.
3. Import the complete reviewed `baseline16.vil` in Vial. Importing the old six-layer file is not the sixteen-layer migration.
4. Export again and compare every layer, encoder, timing, macro, Tap Dance, combo, override and setting with the preset. Check global RGB separately because `.vil` does not contain it.
5. Close Vial, start KeyPeek and the helper, and run the physical checks below. Try experimental16 only after the baseline passes; baseline16 restores ordinary Space.

No step in that procedure has been executed for this feature.

## Build and run

Initialize pinned submodules and the project-local build environment as described in the root README. `vial-qmk-init` applies the reviewed source hooks and refuses an unexpected source revision or content.

```sh
python3 tools/command_mode_assets.py check
devenv shell -- qmk-bootstrap
devenv shell -- sh -c 'make kb=crkbd vial-qmk-init && make kb=crkbd kr=rev4_1/standard km=vial vial-qmk-compile'
swift test --package-path tools/CommandModeHelper
swift build -c release --package-path tools/CommandModeHelper
tools/CommandModeHelper/.build/release/command-mode-helper dry-run --observe-apps --seconds 8
```

Dry-run constructs only a mock transport. Native `run` and `status` require the built `Corne v4 CM1` product/release descriptor, then verify protocol, UID, schema and registry. Unsupported descriptors receive zero output reports. The helper uses nonseizing IOHID and never subscribes or unsubscribes KeyPeek. Its start and every explicit resume open a fresh disarmed session. Select Auto again on the keyboard.

The foreground CLI accepts `status`, `pause`, `disable`, `resume` and `quit` on stdin. Ctrl-C quits cleanly. Native Vial running in the background pauses and releases the helper; configuration traffic also revokes firmware authority. Use explicit pause for browser configurators. Resume requires a deliberate command after configuring. No login item, LaunchAgent or other autorun is installed. To uninstall, quit and delete the built helper; the source/build directory can be removed independently. [Helper details](../tools/CommandModeHelper/README.md). [Raycast update and test steps](raycast-typing.md).

The shared Raw HID interface carries Vial replies, KeyPeek events and private command replies. A passive nonseizing receive-only probe observed existing KeyPeek traffic while KeyPeek remained running and sent zero reports. This proves one read-coexistence case. Mixed-client command writes, launch orders and post-flash reconnect behavior still require hardware testing.

## Validation and remaining physical checks

CI checks generated assets, exact preservation, numeric controls, actual QMK tapping/source-cache/release paths, mode/protocol behavior, USB lifecycle, KeyPeek's sixteen-bit packets, RGB output restoration, native Swift tests, and firmware builds. The boot fixture compiles actual pinned storage/settings/initialization code and simulates interruption after every changed byte, then confirms repeat boots perform no writes. These are software proofs with substituted hardware I/O.

Before adopting the candidate physically, check Menu single/hold/double and interruption timing, every selector and cancel/Home, FN tri-layer, both halves and all extra keys/encoders, momentary mirror and held-key releases, rolling home-row taps and experimental Space order, left-only mouse review, all colors/off/suspend, KeyPeek high-layer display, Vial pause, helper launch orders/reconnect/suspend, and stale focus after Home. QMK press ownership prevents remapping a held action; a fresh mirrored/unmirrored press that collides with its logical slot is consumed until the old owner releases, so release and press it again.

Public ports changed: Menu/control gestures, private versioned HID protocol, helper CLI, registry/preset generator and checked build hooks.

Protected paths touched: EEPROM initialization and native HID output. Tests use fake storage/mock transports; no live reset/import/flash or command-mode write was performed.

Evidence: CI jobs plus the reproducible commands above, `tests/command_mode_test.py`, `tests/storage_bootstrap.py`, `tests/keypeek_packet.py`, `tests/command_mode_assets.py`, lighting tests and `tools/verify_command_mode_build.py`.
