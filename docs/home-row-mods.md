# Restore home-row modifiers in command mode

Use [home-row-mods16.vil](../presets/command-mode/home-row-mods/home-row-mods16.vil) with the Corne v4.1 standard command-mode firmware already installed on both halves. The preset restores your exact base hold families, real Tab keys and physical Shift positions. Keep the installed firmware and helper. No new flash is required.

This file is based on the verified installed baseline16. No fresh live device export was read for this change. You have already confirmed Mouse mode, Chrome and Claude Auto selection, and Home on the installed setup. The new home-row mappings still require the manual checks below.

## Check your current layout before import

1. Double-tap Menu to return Home and disarm Auto.
2. Type `pause` in the existing helper terminal. Wait for its paused status.
3. Quit KeyPeek.
4. Open Vial and export a fresh current layout to a new `.vil` file. Keep that file for rollback.
5. From the repository root, compare the export without writing to the keyboard:

   ```sh
   python3 tools/home_row_mods_preset.py --compare-current /absolute/path/to/current-export.vil
   ```

   `Current export matches verified baseline16` means this preset can replace the verified source without losing other edits. Formatting and object-key order do not affect the check. Every layout cell, encoder, setting, macro, Tap Dance, combo, override and other saved field participates in the comparison.

   If the tool reports drift, keep the fresh export and reconcile it before importing. Importing this preset over newer changes would replace those changes. An export that already matches home-row-mods16 needs no import.

6. After a baseline match, import the complete `home-row-mods16.vil` in Vial.
7. Export again and compare the result with the same command. Expect `Current export already matches home-row-mods16`.
8. Close Vial.
9. Start KeyPeek again.
10. Type `resume` in the helper terminal. Wait for its ready status.
11. Hold Menu and select V to enable Auto deliberately.

The comparison reads local files only. It never opens HID or imports a preset. Global RGB is not stored in `.vil` files and is outside this comparison.

## Check the restored controls

1. In Typing, Numbers and Symbols, hold your usual home-row Command past 200 ms and press your usual Tab. Check native Command-Tab.
2. Add left Shift, then right Shift, in separate checks. Check native Shift-Command-Tab. Release the keys in both orders and check that no modifier remains held.
3. In Chrome and Claude Auto panels, repeat the Command-Tab checks with both left and right home-row Command keys.
4. Tap the home-row keys briefly. Check the original letters, symbol taps and command-panel arrow taps. A fast roll released before 200 ms remains a tap under your unchanged timing settings.
5. Hold Mirror in a command panel and check the opposite cluster, Tab and Shift. Double-tap Menu to return Home, then release held keys. Check ordinary typing resumes.
6. Confirm that normal and mirrored Shift and FN do not invoke a voice shortcut. The OpenAI F18 action and Claude's guarded dictation chord each have one logical binding on the left bracket auxiliary key, matrix 0,6. Mirror moves access to the right bracket auxiliary key at 4,6. The left Backspace thumb stays unused because its mirrored partner is right FN.

The [controls reference and exact difference list](../presets/command-mode/home-row-mods/README.md) identify every changed position. Menu, Home, FN, Mirror, normal Space, specialized Mouse and Picker layers, encoders and saved timing settings remain unchanged.

To undo this trial, return Home and pause the helper, quit KeyPeek, and import the fresh pre-import export you saved. Close Vial before you resume the helper and KeyPeek. Select Auto again only when you want app following.
