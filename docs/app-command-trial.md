# Try the app command preset

Use the separate [Vial 0.7.5 import preset](../presets/command-mode/app-trial/app-trial16-vial075.vil) with the existing Corne command-mode firmware and helper. No flash or helper change is needed. This trial has not been imported or physically tested on the Corne.

The non-import logical reference `app-trial16.vil` has exactly 121 changed key cells from the verified home-row preset. The import file makes eight additional spelling changes on Picker15 so stock Vial 0.7.5 preserves `USER16` through `USER19` as their numeric values. Do not import the logical reference or the repository's source file directly in stock Vial 0.7.5. See the [exact diff and encoding explanation](../presets/command-mode/app-trial/README.md).

## Save and check before import

1. Double-tap physical Menu to return Home and disarm Auto.
2. Type `pause` in the existing helper terminal and wait for its paused status.
3. Quit KeyPeek.
4. Open Vial. Use **Refresh** or reconnect the connected keyboard so Vial rereads the device. Then choose **Save current layout** and save a fresh `.vil` export to a new file. Keep it as your rollback backup.
5. From the repository root, run the new local-file comparison:

   ```sh
   python3 tools/app_command_trial_preset.py --compare-current /absolute/path/to/fresh-before-trial.vil
   ```

   A `source: Current export matches verified home-row-mods16` result permits proceeding over the verified source. A distinct `legacy-source:` result also permits this specific reconciliation: every source field matches except all eight Picker15 cells for `USER16` through `USER19` have become `KC_NO`, exactly as stock Vial 0.7.5 imports them. The trial restores those four duplicated selectors in eight cells and applies the intended 121 changes. No live state is assumed until this fresh comparison. Partial loss or any other change is drift. It accepts equivalent Vial 0.7.5 keycode spellings, formatting and object-key order. A `candidate:` result means the trial is already present and needs no import. A `drift:` result or any error means stop and reconcile the fresh export. Do not import over drift.

6. After a `source:` or exact `legacy-source:` match, use **Load saved layout** to import [app-trial16-vial075.vil](../presets/command-mode/app-trial/app-trial16-vial075.vil).
7. Use Vial **Refresh** or reconnect again to reread the keyboard after import. Save that newly read state to a different file, then compare it:

   ```sh
   python3 tools/app_command_trial_preset.py --compare-current /absolute/path/to/fresh-after-trial.vil
   ```

   Expect `candidate: Current export already matches the app trial`. Any other result needs investigation before using the trial. The comparison includes every layout cell, encoder, macro, setting, Tap Dance, combo, key override, alternate repeat key and other saved field. A missing Picker binding in the post-trial export is drift. The new candidate must retain all eight restored Picker bindings.

8. Quit Vial with **Command-Q**. Closing its window can leave it running.
9. Start KeyPeek again and reconnect or refresh its cached layout so it reads the new mapping.
10. Type `resume` in the helper terminal and wait for its ready status.
11. Hold Menu and select V to enable Auto explicitly only when you want app following. Home disarms Auto.

The tool reads local files only. `--compare-current` and `check` write nothing. `generate` writes only the named trial output files after the source SHA256 gate. None of these commands open HID, import layouts, launch apps or change preferences. Global RGB is not stored in `.vil` files and is outside this comparison.

## Check the changed keys

In command panels 6, 7, 8, 9, 10 and 13, all five row pairs have moved. Undo/Cut/Copy/Paste now sit on left Z/X/C/V and the mirrored cluster. T/Y are Home and disarm Auto. B/N are Command-F Find. Menu double-tap remains the absolute Home fallback, including when you do not know the active panel.

Check ordinary taps, home-row modifier holds, Command-Tab, Shift-Command-Tab and releases on both halves. Repeat with Mirror held. Check Menu, FN, Mirror and Typing Space. Numbers, Symbols, Mouse11, Review12, Picker15 and Maintenance3 keep their behavior. Return Home while keys are held, release them, and check ordinary typing resumes without a stuck modifier.

On OpenAI7:

1. Use Q / right P for the previous sidebar item and W / right O for the next. Each sends Option-Command-Left or Option-Command-Right. Check both directions from your unsent composer draft.
2. Click the unsent draft before dictation. Sidebar navigation can leave HTML content focused.
3. Use the left bracket auxiliary at matrix 0,6 for the existing one-tap Option-Command-Space dictation shortcut. Check Mirror access from the paired physical auxiliary. Its logical 4,6 binding remains `KC_NO`.
4. Check an intended dictation start/stop and that the transcript reaches the unsent composer. Sending a prompt is not part of this check.
5. Confirm that ordinary and mirrored Shift and FN do not start dictation. Claude8 keeps its existing Control-Option-Shift-D auxiliary chord.

The installed `/Applications/ChatGPT.app`, bundle `com.openai.codex`, version 26.1016.61520, build 21421, already has the one-tap Option-Command-Space shortcut enabled. The human confirmed that its recording indicator appeared. Native sidebar navigation passed in both directions, including with composer focus. Full dictation, transcript insertion and Corne emission remain pending. No app preference change is needed. The official [commands reference](https://learn.chatgpt.com/docs/reference/commands#keyboard-shortcuts) and [dictation guide](https://learn.chatgpt.com/docs/prompting#use-voice-dictation) describe the app controls.

## Undo with the fresh rollback backup

1. Double-tap Menu for Home, pause the helper, quit KeyPeek and open Vial as above.
2. Use Vial Refresh or reconnect to reread the keyboard, then save a fresh export of the current state. Compare it and require `candidate:` before replacing the trial. Keep it if you need to investigate drift.
3. Compare your original fresh pre-import backup with the same tool. Require `source:` or the exact `legacy-source:` status you recorded before the trial. Use that backup, which already contains valid Vial export spellings. Rolling back a legacy-source backup also reinstates its eight `KC_NO` cells. Keep the comparison result explicit. Do not substitute the canonical repository source.
4. Import that fresh pre-import backup, use Vial Refresh or reconnect to reread the keyboard, then export again to a new file. Require the same `source:` or `legacy-source:` status as the backup. The exact legacy-source profile intentionally retains its eight original `KC_NO` cells during rollback.
5. Quit Vial with Command-Q, restart KeyPeek and refresh its cached layout, then resume the helper. Enable Auto explicitly only if wanted.

All generated file hashes and the separate representation list are in the [trial manifest](../presets/command-mode/app-trial/manifest.json). Historical presets and output packets remain unchanged.
