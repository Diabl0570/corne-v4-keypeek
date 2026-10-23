# Firmware CI

The [Corne firmware workflow](../.github/workflows/firmware.yml) builds the personal keyboard target, **Vial Corne v4.1 standard**, on pull requests and the configured push branches. The command-mode checks and native Mac helper tests also run. A successful firmware build uploads `vial-rev4_1-standard`, including its UF2, checksums, compiler and dependency versions, and command-mode build verification.

## Compatibility builds

In GitHub Actions, select **Corne firmware**, then **Run workflow**. Choose the branch and enable **Build all six Vial/VIA compatibility targets** (`full_matrix`) to build:

| Route | Revision | Size |
| --- | --- | --- |
| Vial | v4.0 | standard |
| Vial | v4.1 | standard |
| VIA | v4.0 | standard |
| VIA | v4.1 | standard |
| VIA | v4.0 | mini |
| VIA | v4.1 | mini |

Without that option, a manual run builds only Vial v4.1 standard. The other targets check compatibility; they are not firmware choices for this keyboard. Command mode is compiled only into the Vial v4.1 standard target.

## When documentation skips CI

Automatic runs ignore changes limited to `docs/**`, `README.md`, and `**/README.md`. Generated preset documentation, such as `presets/command-mode/legend.md`, remains checked. Helper source changes still run the workflow, including the one firmware target, so shared protocol and registry checks stay together.

GitHub evaluates pull-request path filters against the cumulative PR diff. A documentation-only follow-up in a PR that also changes firmware therefore still runs CI. A new documentation-only PR, or a documentation-only push to a configured branch, can skip it. See [GitHub's diff rules](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#git-diff-comparisons).

Path-filtered workflows can leave required checks pending. If these checks become required by branch protection, replace workflow-level skipping with an always-running status check before relying on documentation-only merges.

## Setup limits and caching

Each firmware job has a 15-minute limit. OS and Python dependency installation have separate five-minute limits, so a stalled setup fails with a specific step name. APT uses 30-second HTTP and HTTPS timeouts, two retries, and noninteractive installation. Recommended compiler packages remain enabled.

A newer run of this workflow on the same Git ref cancels the older run. Manual runs on that same ref also share this concurrency group.

The Python cache uses all four dependency inputs: `requirements-qmk.txt`, `requirements-qmk.lock`, `src/vial-kb/vial-qmk/requirements.txt`, and `src/qmk/qmk_firmware/requirements.txt`. Both upstream requirement files remain inputs even for a Vial-only build. Installation and `pip check` still run after a cache hit. APT packages, patched QMK source trees, and firmware build outputs are not cached.

These limits bound a stalled dependency installation; they do not identify its cause. Compilation and artifact verification must pass before a run supplies firmware for flashing. CI does not test the physical keyboard or perform a flash.
