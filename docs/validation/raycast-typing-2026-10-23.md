# Raycast typing verification, 2026-10-23

## Tested configuration

- Corne v4.1 standard with firmware registry `75ADDACE` and the existing 16-layer layout.
- The user confirmed both halves were flashed. The connected half passed the native capability check.
- Mac helper source `c59f72dd45670b98601ae9adaf29cc350bc1b42e`.
- Installed helper SHA256 `4588e146e3564290de53f52eb8954031273615a7c60ef6c1bcb9e7681cf50ecd`, matching the packaged binary.
- Raycast 2.9.0.0 and the installed KeyPeek 0.10.0 build with custom labels.
- The helper runs through the separately installed user login service.

## Results

All 62 Swift tests, the release build, and the mock CLI regression checks passed. The panel-detection regression failed before the fix and passed afterward. These checks cover software behavior; they do not establish physical text entry.

With Auto enabled, native firmware readback recorded OpenAI layer 7, Typing layer 0 while Raycast was visible, and OpenAI layer 7 after dismissal. The same session remained active with no retries during the final sequence.

With KeyPeek connected and the helper running, the user confirmed the complete flow. Raycast opened, the layer changed to Typing, `calculator` appeared in Raycast, and Escape restored OpenAI. The helper error log was empty after this test.

The enabled service reached `phase=ready` after being stopped and started for KeyPeek initialization. Actual logout and login were not tested.

## Focus issue encountered during validation

Initially, the correct Typing layer appeared but physical keystrokes went to the previous application. The MacBook keyboard reproduced the same routing failure. UI automation could enter text in Raycast, so that automation result alone was insufficient.

Typing recovered after KeyPeek was closed and Raycast was restarted. The user also restarted Raycast during the comparison, so this does not isolate either application as the cause. KeyPeek was then connected with the helper stopped, and the helper was restarted. The full physical test passed with both running.

No focus-forcing code, firmware change, or preset import was made for this recovery. The cause of the temporary focus failure remains unisolated. Concurrent KeyPeek initialization also remains a known issue, with the startup-order workaround in the [recovery instructions](../raycast-typing.md#recover-when-text-goes-to-another-window).
