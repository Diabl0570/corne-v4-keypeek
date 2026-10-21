# Update the firmware and dependencies, then add active-layer lighting

Open a pull request against `Diabl0570/corne-v4-keypeek` after completing both requirements. Do not flash a device or merge the pull request.

## Establish the baseline

1. Clone recursively and record the starting commit.
2. Follow the root README and build both `rev4_0/standard` and `rev4_1/standard` Vial targets.
3. Inspect `layouts/corne-v4-before-2026-10-21.vil`, the keymap, and the KeyPeek module before changing code.
4. Record any baseline failure separately from failures introduced by the upgrade.

The connected keyboard reports foostan Corne v4, USB VID `0x4653`, PID `0x0004`, and device version `0x0410`. Both standard revision definitions use device version 4.1.0. These descriptors and an old UF2 filename do not establish the physical revision. Preserve both build targets until physical evidence resolves it.

## Update the firmware and dependencies used by this workspace

Inspect current upstream releases and compatibility. Update the firmware sources and the dependencies actually used by the project. Explain selected versions, excluded incompatible versions, and migration work in the PR. Do not run a blanket update and assume the result works.

The publication pins are:

| Dependency | Starting revision |
| --- | --- |
| QMK firmware, `src/qmk/qmk_firmware` | `33a12ca0b67d9b70e819d1d5fb9125f6b50cb943` |
| Vial-QMK firmware, `src/vial-kb/vial-qmk` | `dd43959ae5c08d8a28d38a1acf7b04e86b14a344` |
| KeyPeek QMK modules, `modules/srwi` | `8f120e29fec27a0aeb63b4c4f63c6a70e3225fb3` |
| devenv module | `4b10b32036245a13efdb0d77d69d6990d1c8a3f5` |
| nixpkgs | `ffb3c9b700e759be2ef13237c9d8f953b32a1e46` |

Inventory the nested firmware submodules with `git submodule status --recursive`. Review `devenv.nix`, `devenv.lock`, `requirements-qmk.txt`, and each firmware's Python requirements. The QMK CLI requirement currently has no version constraint. Make the resulting setup reproducible where practical. Keep firmware changes and toolchain changes reviewable.

Preserve Vial's dynamic keymap compatibility, the six-layer layout export, tap/hold settings, USB identity, and KeyPeek raw HID notifications and commands. The current integration disables the module's built-in handler and calls `keypeek_handle_command` through `raw_hid_receive_kb`. Recheck the APIs after upgrading.

## Implement automatic active-layer lighting

Use RGB Matrix indicators or another firmware mechanism supported by the selected Vial-QMK revision. The Vial Lighting UI exposes global effect, color, brightness, speed, and Save controls. It has no observed per-layer rules.

- Derive the displayed layer from the highest active layer in `layer_state | default_layer_state`.
- Handle both toggled layers and momentary layers. Restore the previous active layer or the base effect on release or toggle-off.
- Make the state visible on both halves. Inspect and configure split transport and state synchronization as required.
- Respect RGB on/off, the brightness setting and firmware cap, and user preferences. Preserve the base effect for restoration.
- Do not write EEPROM on layer transitions.
- Preserve mappings, home-row modifiers, tap/hold timing, Vial features, and KeyPeek.

The current layout has these roles:

| Layer | Role |
| --- | --- |
| 0 | QWERTY and home-row modifiers, `TG(1)` and `FN_MO23` on the thumbs |
| 1 | Numbers and right-hand arrows |
| 2 | Shifted numbers and coding symbols |
| 3 | RGB and maintenance controls, `QK_BOOT` at top left |
| 4 and 5 | Fully transparent, reserved |

Confirm `FN_MO23` semantics in the selected firmware. A starting palette is green for layer 1, purple for layer 2, and amber for layer 3. Keep reserved layers readable without inventing new roles or activation keys. Suggest workflow improvements separately, grounded in the current keymap. Do not apply blanket remapping.

## Verify and open the pull request

Build both standard Vial variants after upgrades and lighting changes. Verify the stock VIA build route for the maintained Corne targets when the QMK dependency changes. Add focused checks for highest-layer selection, overlapping layers, release restoration, and disabled lighting where the code allows it. Inspect Vial and KeyPeek callback composition and ensure layer transitions do not save EEPROM.

Report exact commands, dependency revisions, artifact hashes, failures, and remaining hardware checks. Cloud compilation does not verify physical LEDs. Leave physical tests for base lighting, `TG(1)` on/off, the momentary path, overlapping layers, both halves, reconnect, and persisted preferences as explicit follow-up.

Keep a layout rollback path through Vial's saved-layout import. Restore RGB separately using the recorded global values. The exported layout is not an installed-firmware backup. Do not select rollback firmware until the PCB revision is confirmed.

References are [Vial lighting](https://get.vial.today/docs/lighting.html) and [QMK RGB Matrix indicators](https://docs.qmk.fm/features/rgb_matrix#indicators). Check the documentation against the selected source revision.
