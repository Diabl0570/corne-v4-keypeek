# Device label profiles

This directory preserves the local KeyPeek patch used with this Corne firmware. It applies to upstream KeyPeek 0.10.0, commit `d7f5a89276c46285d45c1fb69ca9bc42d8b249a6`. The profile is independent of the Raycast firmware update and works with the existing 16-layer command firmware.

## Rebuild the local application

Clone `https://github.com/srwi/keypeek.git` at tag `0.10.0` into a separate directory. Apply `corne-labels.patch` from this directory with `git apply`, then run:

```sh
cargo fmt --all -- --check
cargo test --release --locked
cargo build --release --locked
```

The executable is `target/release/keypeek`. Preserve the existing KeyPeek app bundle before replacing its `Contents/MacOS/keypeek` executable. Sign the assembled local app with `codesign --force --deep --sign - /path/to/KeyPeek.app`, then verify it with `codesign --verify --deep --strict /path/to/KeyPeek.app`. Quit KeyPeek before replacing the installed app. Copy this directory's `labels.json` to the configuration path below. Start KeyPeek and reconnect the Corne.

This is a local patch, not an upstream KeyPeek release. Stock updates replace the patched executable. Keep the patch and profile together for future rebuilds.

## Use the labels

This local KeyPeek build can name layers and custom keys using a `labels.json` file next to `settings.ini`. Labels affect the overlay and layer names in the editor and settings. They do not change the keyboard's bindings or firmware.

On macOS the file belongs at:

```text
~/Library/Application Support/dev.srwi.KeyPeek/labels.json
```

Copy this directory's `labels.json` there and restart KeyPeek. That profile matches the Corne command firmware's VID, PID, Vial UID, 8×7 matrix and 16 layers. A different identity or layer count keeps the ordinary KeyPeek labels. An invalid profile is ignored and reported on standard error. Keep any existing profile as a backup before replacing it.

The overlay shows the active layer above the keys, for example `OpenAI · L7`, `Browser · L9` or `Picker · L15`. When the keymap editor previews a layer, the heading follows that preview. The heading names the layer; it does not indicate whether Auto Command is enabled. Layer 0 is called Typing, so Raycast can show Typing while Auto remains armed. The Home key still exits command mode.

The included profile names the physical Menu key and the command firmware's custom actions:

| Action | Display |
| --- | --- |
| Physical matrix row 3, column 3 | Menu |
| `0x7e00` | Home |
| `0x7e01` | Auto |
| `0x7e02` | Mirror |
| `0x7e03` | Space / Mirror |
| `0x7e04` through `0x7e13` | Typing, Numbers, Symbols, Maintenance, Reserved 4, Reserved 5, Commands, OpenAI, Claude, Browser, Editor, Mouse, Review, Experiments, Spare, Picker |

To change a name, edit `text` in the relevant entry. `short` is an optional compact label used when the key is small. `target_layer` is optional and supplies the destination layer's color. The keycode keys in JSON use decimal numbers; for example `32257` is `0x7e01` (Auto). Code labels follow their binding when you move it in Vial. Position labels remain at their specified matrix coordinates, which is appropriate for the Menu key intercepted by this firmware. Positions can optionally include `layer` to restrict a label to one layer.

The layer names are an ordered list starting at layer 0. The number of names must match the keyboard's layer count. Layer names, text labels and position coordinates are validated when KeyPeek connects. Changes to the file take effect after restarting KeyPeek.

To undo the labels, rename or remove `labels.json` and restart KeyPeek. Your saved `settings.ini`, home-row modifiers and actual key assignments stay intact. A stock KeyPeek update will require this local patch to be rebuilt; the profile file alone does not add this feature to stock 0.10.0.
