# Command-mode hooks for the pinned Vial source

`hooks.patch` applies only to Vial commit `dd43959ae5c08d8a28d38a1acf7b04e86b14a344`. The manifest pins the patch and every changed source file with SHA256. All behavior changes require `COMMAND_MODE_ENABLE`. Other builds retain upstream behavior.

The patch tool checks the commit, patch hash, source hashes, unrelated tracked edits, and unexpected untracked source before writing. It accepts an entirely original or entirely patched tree. It rejects partial application. The build's generated `keyboards/tmp/` inputs are permitted. Repeated application verifies the patched hashes and changes nothing.

```sh
python3 tools/apply_command_mode_patches.py --check
python3 tools/apply_command_mode_patches.py
```

Use `--source PATH` when the initialized pinned submodule lives elsewhere. The tool changes the checkout's source files without changing its commit or the parent's submodule pin.

The early call runs after `eeprom_driver_init()` and before `vial_init()` or the first `qmk_settings_init()`. The VIA validity bytes become the fixed schema marker `01 4D 43`, corresponding to `0x434D01`. Random build IDs cannot reset a compatible image. Any change to the dynamic EEPROM layout or incompatible seed semantics requires a new reviewed marker.

`command_mode_storage_reset()` invalidates the marker before dependent writes. It seeds the compiled sixteen-layer personal maps and encoders, captured QMK settings, empty Tap Dances with the configured tapping term, empty combos and alt repeats, default inactive overrides, and empty macros. It writes the valid marker after the complete seed. It never copies bytes from an old layout.

The early seed skips setting ID 21, which controls core keymap flags rather than relocated QMK settings. Existing valid core EEPROM, including RGB settings and keymap flags, remains unchanged. Blank or invalid core EEPROM uses QMK's normal core defaults. Its validity is committed after the full initialization so interrupted core initialization repeats. `eeconfig_init_via()` uses the same dynamic initializer, which prevents later VIA or core initialization from undoing the personal seed.

The settings table is generated as `cm_initial_settings[]` in `command_settings.h`. Every entry has a `uint16_t id` and `uint32_t value`. An unsupported generated ID halts before storage becomes valid. Each value is serialized as four little-endian bytes for the pinned `qmk_settings_set()` API.

The other hooks expose `action_tapping_is_idle()`, call `command_mode_pre_action(keyevent_t)` before swap and source lookup, and call `command_mode_configuration_activity()` before VIA dispatch. Tapping idle requires no tapping event, an empty waiting queue, and no registered chordal or flow taps. Configuration admission ignores helper `D3` and KeyPeek `C0` report families.

The host tests use only fake EEPROM. They compile the actual bootstrap, pinned settings and dynamic EEPROM code, and the patched boot, VIA, and core initialization functions. They simulate a power cut before every changed EEPROM byte write, reboot, compare the whole image with an uninterrupted seed, and verify that a second valid boot writes zero bytes. Existing core and RGB bytes must remain equal. The tests also reject wrong source pins, modified source, unrelated tracked edits, unexpected source files, and partial patch application.

```sh
python3 tests/storage_bootstrap.py --source src/vial-kb/vial-qmk
python3 tests/storage_bootstrap.py --source src/vial-kb/vial-qmk \
    --settings keyboards/crkbd/vial-kb/vial-qmk/keymaps/vial/command_settings.h
```

These tests do not establish physical flash atomicity or hardware behavior. The future authorized flash session must explicitly import the reviewed baseline16 preset in Vial and read back the full configuration. That import restores every captured setting, including ID 21, Tap Dances, macros, combos, overrides, and encoders. Retain the old firmware and fresh six-layer export for rollback.

Public ports changed are the checked patch CLI, bootstrap/reset functions, physical-action hook, configuration-activity hook, and tapping-idle query.

Protected paths touched are the EEPROM initialization path and the patch tool's source writes. Tests perform no device writes.

Evidence includes the fake-EEPROM power-loss suite, actual pinned boot-order and settings code, full image comparisons, core preservation, and patch rejection/idempotence checks. Firmware compilation and physical verification remain separate checks.
