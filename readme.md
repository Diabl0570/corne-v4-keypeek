# Corne v4 KeyPeek workspace

This is Kasper's Corne v4 firmware workspace, based on [foostan/kbd_firmware](https://github.com/foostan/kbd_firmware). It retains the upstream history, keyboard definitions, Vial configuration, and existing KeyPeek raw HID integration.

Automatic layer lighting and dependency upgrades are the next task. This baseline does not implement them. No firmware was flashed during publication.

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

The `rev4_1/standard` command is a build target, not a confirmed identification of the connected PCB. The physical revision remains unresolved. Use `kr=rev4_0/standard` to compile the other standard variant. Do not flash either artifact until the PCB revision is established.

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

[The current Vial export](layouts/corne-v4-before-2026-10-21.vil) contains six layers and the current tap/hold settings. The older `corne v4.vil` remains as a historical backup. The C keymap contains firmware defaults and must not replace the current device layout without an explicit migration plan.

The `.vil` files do not contain RGB settings. The observed lighting was Cycle Left Right, red `#FF0000`, brightness 50, and speed 127. [Baseline metadata](docs/baseline-2026-10-21.json) records the observations and limitations.

## Continue development

[The cloud task](docs/cloud-task.md) covers firmware and dependency updates, automatic layer lighting, verification, and a pull request. Preserve the current mappings, timings, KeyPeek, and Vial capabilities.

## Provenance and licenses

The upstream baseline is `foostan/kbd_firmware@b38479ca28f3787a95cd1984022110482385e3bc`. Six existing local commits end at `65ea692cbc86f0fee947143b7583aa4cd52057cb`. Publication preserves that history and the source notices. [The original build notes](docs/upstream-build-notes.md) remain available.

QMK, Vial-QMK, srwi's QMK modules, and their nested dependencies retain their own license files and copyright notices. This repository does not replace those licenses or assign a new license to upstream code.

Publication excludes local caches, temporary firmware, an empty inspection file, a duplicate nested module registration, and generated firmware from the current tree. Historical upstream build artifacts remain in the preserved upstream history. The existing uncommitted `RAW_ENABLE = yes` change is included.
