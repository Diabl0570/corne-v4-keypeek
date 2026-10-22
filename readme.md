# Corne v4 KeyPeek workspace

This is Kasper's Corne v4 firmware workspace, based on [foostan/kbd_firmware](https://github.com/foostan/kbd_firmware). It retains the upstream history, keyboard definitions, Vial configuration, and existing KeyPeek raw HID integration.

The Vial standard keymap automatically indicates the highest active/default layer: green for numbers, purple for symbols, and amber for maintenance. Base and reserved layers show the selected global RGB effect. RGB off, brightness and the firmware cap remain effective. No firmware has been flashed by the cloud worker.

[Implementation, dependency audit, validation and rollback](docs/layer-lighting.md) records the exact changes and remaining hardware checks.

[Command mode](docs/command-mode.md) adds sixteen layers, Menu picker/Home, momentary hand swapping and an app-context Mac helper for **rev4_1/standard Vial**. The fresh live backup is committed separately before feature work. Review the [physical key legend](presets/command-mode/legend.html), exact baseline/experimental presets and future upgrade/import procedure before flashing.

For the installed command-mode firmware, [restore home-row modifiers and familiar Tab/Shift positions](docs/home-row-mods.md) with the optional `home-row-mods16.vil`. This preset preserves your settings and requires no firmware flash. Compare a fresh Vial export before importing it.

The separate [app command trial](docs/app-command-trial.md) starts from that home-row preset. It puts editing commands on Z/X/C/V, moves Home to T and Find to B in the shared command panels, and adds OpenAI sidebar navigation and native one-tap dictation. It requires no flash or helper update. Its comparison tool recognizes equivalent Vial 0.7.5 keycode exports and rejects layout or settings drift before import.

## Build the pinned Vial firmware

Clone the repository and its pinned dependencies:

```sh
git clone --recurse-submodules https://github.com/Diabl0570/corne-v4-keypeek.git
cd corne-v4-keypeek
```

With Nix and devenv installed, bootstrap the project environment:

```sh
devenv shell -- qmk-bootstrap
devenv shell
make kb=crkbd vial-qmk-init
make kb=crkbd kr=rev4_1/standard km=vial vial-qmk-compile
```

The user's board has been confirmed as Corne v4.1 standard. Command Mode is enabled only for that Vial target. `kr=rev4_0/standard` builds the unchanged six-layer standard variant. The command-mode storage format requires the explicit future preset import described in its guide.

The Vial artifact is `src/vial-kb/vial-qmk/.build/tmp_crkbd_rev4_1_standard_vial.uf2`. The Makefile also copies it into `keyboards/crkbd/vial-kb/vial-qmk/.build/`. Generated firmware is ignored by Git.

For a Linux worker without Nix, install the QMK prerequisites, including Python with venv, Make, Git, `arm-none-eabi-gcc`, newlib, and USB development libraries. Then run:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-qmk.txt
export QMK_HOME="$PWD/src/vial-kb/vial-qmk"
export QMK_USERSPACE="$PWD"
make kb=crkbd vial-qmk-init
make kb=crkbd kr=rev4_1/standard km=vial vial-qmk-compile
```

Use `git submodule update --init --recursive` to restore the pinned dependencies. The legacy `make git-submodule` and `make update-all` targets advance upstream revisions and are unsuitable for reproducing this baseline.

## Preserve the device layout

[The fresh live Vial export](backups/2026-10-21-live/corne-v4.1-live-2026-10-21-1631.vil) contains six layers and the captured tap/hold settings. The earlier export in `layouts/` and `corne v4.vil` remain historical backups. The command-mode compiled seed and sixteen-layer presets are generated from the fresh export; the other targets retain their existing defaults.

The `.vil` files do not contain RGB settings. The observed lighting was Cycle Left Right, red `#FF0000`, brightness 50, and speed 127. [Baseline metadata](docs/baseline-2026-10-21.json) records the observations and limitations.

## Continue development

[The cloud task](docs/cloud-task.md) preserves the original requirements. Preserve the current mappings, timings, KeyPeek, and Vial capabilities.

## Provenance and licenses

The upstream baseline is `foostan/kbd_firmware@b38479ca28f3787a95cd1984022110482385e3bc`. Six existing local commits end at `65ea692cbc86f0fee947143b7583aa4cd52057cb`. Publication preserves that history and the source notices. [The original build notes](docs/upstream-build-notes.md) remain available.

QMK, Vial-QMK, srwi's QMK modules, and their nested dependencies retain their own license files and copyright notices. This repository does not replace those licenses or assign a new license to upstream code.

Publication excludes local caches, temporary firmware, an empty inspection file, a duplicate nested module registration, and generated firmware from the current tree. Historical upstream build artifacts remain in the preserved upstream history. The existing uncommitted `RAW_ENABLE = yes` change is included.
