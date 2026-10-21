# Layer lighting and dependency update (2026-10-21)

Starting point: `418dba3f286fa0eb672ca97f9628fe10f95334ef`, cloned with
`git clone --recursive`. No repository `AGENTS.md` was present. The root README,
`docs/cloud-task.md`, fresh saved layout and KeyPeek module were read before edits.
`pstack:poteto-mode` was not available in this worker's skill catalog.

## Plan and investigated subsystems

1. Build both pinned Vial standard revisions before changing firmware.
2. Inspect upstream versions, requirements, nested pins, RGB rendering/transport,
   Vial raw HID routing, KeyPeek community hooks and the saved layout.
3. Name the state model before implementation: a six-entry `layer_indicators`
   HSV table, indexed by the highest bit of `layer_state | default_layer_state`.
4. Keep dependency upgrades, required compatibility migration, lighting and
   verification/documentation in separate review commits.
5. Review restoration and callback composition separately from implementation;
   compile both Vial targets and all four maintained Corne v4 VIA variants.

## Resulting behaviour

| Highest active or default layer | Output |
| --- | --- |
| 0 | User's global effect |
| 1 | Green (HSV hue 85, saturation 255) |
| 2 | Purple (hue 191, saturation 255) |
| 3 | Amber (hue 30, saturation 255) |
| 4/5, or outside the table | User's global effect; no invented role |

`FN_MO23` is Vial's name for `TL_UPPR` / `QK_TRI_LAYER_UPPER` (`0x7C78`).
In the selected source, `process_tri_layer.c` holds upper layer 2 and updates
adjust layer 3 using lower layer 1. Thus, alone it displays purple; while
`TG(1)` is active it displays amber. Releasing it returns to green if layer 1
remains active, otherwise to the global effect. Layer 1 may also be toggled off
while upper is held; the indicator always derives from the resulting state.

The adapter is scoped to the standard **Vial** keymap. The maintained **VIA**
route retains its previous stock behaviour and receives only the QMK keycode
compatibility migration. Neither path replaces the saved personal layout.

### Why an output adapter rather than an ordinary indicator

Review found that a plain RGB Matrix indicator writes into the effect's buffer.
Sparse effects such as Raindrops only repaint selected LEDs, so release can leave
stale layer colours. The small custom RGB Matrix driver delegates initialization
and LED output to the existing WS2812 vendor driver, shadows effect colours,
applies the table colour only during flush, then restores the effect buffer.
This preserves both continuously repainted Cycle Left Right and sparse effects.
The selected RP2040 `ws2812_vendor.c` copies colours into a separate DMA buffer
before `ws2812_flush()` returns, making that immediate restoration safe. This
assumption must be revisited if the underlying WS2812 driver changes.

Output uses current brightness capped at the existing firmware maximum (50),
respects RGB enable, suspend, configured inactivity timeout, and LED flags.
No mode, HSV preference, speed or enable state is changed by layer transitions.
There are no EEPROM/config setters in the adapter. Effects continue running
underneath; restoration resumes the effect, rather than restarting it.

`SPLIT_LAYER_STATE_ENABLE` transmits **both** active and default layer states.
The existing `RGB_MATRIX_SPLIT {23, 23}` transport also synchronizes RGB
configuration and suspend state. The custom adapter keeps the normal local
WS2812 indices and checks the matching half's global LED flags. No additional
RPC, keypress tracking or independent toggle state is introduced.

Vial's `via.c` handles its normal commands first and routes unknown commands to
`raw_hid_receive_kb`; the existing keymap bridge still calls
`keypeek_handle_command`. The built-in module raw HID handler remains disabled.
KeyPeek layer/key notification hooks remain in generated community-module
composition. The adapter defines neither a layer-state nor a record callback.
Mainline QMK still has `via_command_kb`; its stock VIA build does not enable
KeyPeek, matching the baseline route. No new migration to VIA's separately
maintained community module is needed during QMK 0.34's compatibility period.

## Dependency selection

Upstream refs were checked directly with `git ls-remote` and local release tags.
The QMK breaking-change notes from 0.29 through 0.34 were inspected, especially
removed RGB aliases, community-module APIs and VIA migration.

| Component | Selected revision / reason |
| --- | --- |
| QMK | **0.34.7**, `180f394b489c238cb231c2bf8b080262155e03c0`, current release tag and master head at inspection; replaces `33a12ca0b67d9b70e819d1d5fb9125f6b50cb943` (0.28.10 plus 3 commits) |
| Vial-QMK | Retain `dd43959ae5c08d8a28d38a1acf7b04e86b14a344`; already current upstream default head, no firmware release tags found. Vial GUI 0.7.5 is not a firmware revision |
| srwi KeyPeek modules | Retain `8f120e29fec27a0aeb63b4c4f63c6a70e3225fb3`; already current upstream head. Requires community API >=1.1.0, supported by selected Vial source |
| QMK CLI | Previously unconstrained; pin **1.2.0**, the version resolved and exercised in this run |
| Python runtime dependencies | `requirements-qmk.lock` constrains all 24 resolved packages for both firmware requirement files; Python 3.12.14 used. Includes milc 2.1.0, jsonschema 4.26.0, Pillow 13.0.0, hid 1.0.9 |
| devenv | Retain `4b10b32036245a13efdb0d77d69d6990d1c8a3f5`; observed newer upstream head `d23b7b31e4a7cde48c53fdfbb010b493c3f8ef57`, deliberately not advanced without Nix/devenv evaluation |
| nixpkgs | Retain `ffb3c9b700e759be2ef13237c9d8f953b32a1e46`; observed nixos-unstable `02c087f3fe673c9e317f206a627cb6b910336dbe`, deliberately not advanced without evaluating the cross compiler and shell on Nix |

Nix and devenv are absent from the cloud worker. The existing lock hashes remain
intact; no unverifiable replacement NAR hashes were fabricated. `devenv.nix`
bootstrap now uses the constrained Python requirements without an unrelated,
unpinned pip self-upgrade. Nix shell evaluation and Mac bootstrap remain untested.
Python locks fix package versions, not platform wheel hashes or OS packages;
firmware binaries are not claimed to be byte-for-byte reproducible across hosts.

QMK 0.34 removed legacy `RGB_*` aliases. The VIA keymap now locally maps its
existing names to `RM_*` for rev4 Matrix or `UG_*` for rev1 underglow, preserving
positions and functionality. Vial stays on its own compatible keycodes.

Nested firmware dependencies follow each selected parent, not independent latest
heads. Full before/after inventories are in `verification/*-submodules.txt`.
The QMK update changes these nested pins:

| Nested QMK dependency | Before | After |
| --- | --- | --- |
| ChibiOS | `2365f844292513ea0ee9eea6ab778d56f9ccd3b9` | `6170ddf92d55be54c89b708d1882eea229edeb2c` |
| ChibiOS-Contrib | `3ac181e4ca5cafddaf8b472baa1d09c2b24c77b6` | `5a9ad82b6ba4f649cdb800e8c2bbc9be2d3ce767` |
| GoogleTest | `e2239ee6043f73722e7aa812a459f54a28552929` | `6910c9d9165801d8827d628cb72eb7ea9dd538c5` |
| Pico SDK | `a3398d8d3a772f37fef44a74743a1de69770e9c2` | `d0c5cac430cc955b65efa0e899748853d9a80928` |

LUFA, LVGL, printf and V-USB stay at the parent-selected pins. MCUX SDK stays at
`102c27d7cc2aaac87c133702e7829a105e0cb433` under ChibiOS-Contrib. Vial's nested pins remain
unchanged. GoogleTest, LUFA, LVGL and V-USB are inventoried even though these
RP2040 builds do not exercise them. Firmware `requirements-dev.txt` files are
optional upstream development/test tools, not this workspace's build requirements.

## Direct validation

| Check | Result |
| --- | --- |
| Baseline Vial rev4_0/standard and rev4_1/standard | Both passed with KeyPeek |
| Final Vial rev4_0/standard and rev4_1/standard | Both passed with custom adapter, VialRGB and KeyPeek |
| Updated QMK VIA rev4_0/standard, rev4_1/standard, rev4_0/mini, rev4_1/mini | All four passed |
| Host test of the actual adapter | Passed with `-Wall -Wextra -Werror -fsanitize=undefined` |
| Locked Python installation and `pip check` | Passed |
| `git diff --check` | Passed |

Worker compiler: Debian arm-none-eabi GCC 12.2.1 (12.2.rel1), binutils 2.40,
newlib 3.3.0; host GCC 13.3.0. Debian packages were extracted into a worker-local
toolchain, with include/library symlinks normally provided by package installation.
An initial baseline attempt failed on missing `assert.h` before those links were
fixed; both unchanged baseline targets subsequently passed. Initial QMK builds
identified the removed RGB aliases, now migrated. An early lighting prototype
used a non-public colour helper and was corrected before final builds. Address
Sanitizer could not run LeakSanitizer under this worker's restricted `/proc`;
the final test uses UndefinedBehaviorSanitizer and explicit index assertions.
No outstanding C compilation failures remain. The legacy Makefile prints a
missing `.hex` copy for UF2 targets; the UF2 compile/link/copy succeeds.

The test calls the actual driver adapter with substituted QMK/WS2812 I/O. It
checks highest active/default selection, overlap, momentary release and toggle-off
restoration, reserved/out-of-range layers, sparse buffer preservation, brightness
zero/cap, RGB off, suspend, timeout, flags and left/right local indices. It does
not simulate electrical split transport, DMA or USB traffic. Source review checks
callback composition and absence of EEPROM writes; compilation is not an on-device
KeyPeek/Vial round-trip test.

Exact commands (from the workspace root, after installing the prerequisites):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-qmk.txt
python -m pip check
export QMK_USERSPACE="$PWD"
export QMK_HOME="$PWD/src/vial-kb/vial-qmk"
make kb=crkbd vial-qmk-init
make kb=crkbd kr=rev4_0/standard km=vial vial-qmk-compile
make kb=crkbd kr=rev4_1/standard km=vial vial-qmk-compile
export QMK_HOME="$PWD/src/qmk/qmk_firmware"
make kb=crkbd qmk-init
make kb=crkbd kr=rev4_0/standard km=via qmk-compile
make kb=crkbd kr=rev4_1/standard km=via qmk-compile
make kb=crkbd kr=rev4_0/mini km=via qmk-compile
make kb=crkbd kr=rev4_1/mini km=via qmk-compile
cc -std=c11 -Wall -Wextra -Werror -fsanitize=undefined tests/layer_lighting.c -o /tmp/layer-lighting
/tmp/layer-lighting
git diff --check
```

Baseline commands were the same Vial commands at the starting commit, with the
baseline's unconstrained requirements (resolved versions recorded in the lock).
Firmware hashes are in `verification/baseline-sha256.txt` and
`verification/selected-sha256.txt`. CI repeats the six final builds and uploads
UF2s, SHA256SUMS, compiler, Python and submodule manifests as named workflow
artifacts, keeping binaries out of source history. CI runner/compiler versions
may differ from this worker; use hashes supplied with each artifact download.

## Physical checks and rollback

Physical revision is still unconfirmed. Both standard definitions report USB
VID `0x4653`, PID `0x0004`, device version 4.1.0; neither that descriptor nor an
old UF2 filename identifies the PCB. No hardware was flashed or tested here.
Before installing firmware, identify the actual PCB and select its matching
revision. Do not choose one merely because both compiled.

After an owner-controlled install, verify both halves, `TG(1)` on/off,
`FN_MO23` press/release alone and overlapping layer 1, toggling layer 1 while
upper is held, base effect restoration (including Raindrops), RGB off/on,
brightness 0/50, reconnect/suspend, persisted global lighting preferences, Vial
editing/unlock and KeyPeek subscribe/keepalive notifications. Also check that
home-row modifiers and saved tap/hold timing behave as before.

For layout rollback, import `layouts/corne-v4-before-2026-10-21.vil` through Vial.
The six-layer export, home-row mappings, Vial UID/unlock, USB identity and timings
are unchanged by this PR. The `.vil` file is **not** an installed-firmware backup
and does not contain lighting preferences. Restore lighting separately to Cycle
Left Right, red `#FF0000`, brightness 50, speed 127, and explicitly save through
Vial if persistence is desired. Firmware rollback means recursively checking out
`418dba3f286fa0eb672ca97f9628fe10f95334ef` and building the **confirmed PCB** target;
no preselected rollback UF2 or previously installed binary is asserted.

Separate workflow suggestions (not applied): retain a dated Vial export after
layout changes; use KeyPeek to confirm the tri-layer path; add an explicit
owner-chosen maintenance entry only if the existing toggle-plus-hold path proves
awkward. No blanket keymap redesign is proposed or implemented.

References: [QMK release source](https://github.com/qmk/qmk_firmware/tree/0.34.7),
[Vial source](https://github.com/vial-kb/vial-qmk/tree/dd43959ae5c08d8a28d38a1acf7b04e86b14a344),
[RGB Matrix indicators](https://docs.qmk.fm/features/rgb_matrix#indicators),
[Vial lighting](https://get.vial.today/docs/lighting.html). Behaviour claims above
were checked against the selected source, rather than assuming current web docs
match Vial's fork.
