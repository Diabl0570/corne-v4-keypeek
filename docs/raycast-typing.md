# Type normally in Raycast during Auto Command

With Auto Command enabled, opening Raycast selects your existing Typing layer0. Your letters, Space, Enter and home-row mods keep their current typing assignments. Dismissing Raycast restores the panel for the foreground app. Raycast running in the background does not change the keyboard.

This uses an existing layer. It does not copy your layout, consume another layer slot, or change a saved preset. Manual panels remain pinned. Physical Home still exits Auto, so dismissing Raycast after Home cannot re-enter a command panel.

## Install the matching pair

The old firmware only accepts automatic contexts6 through10. This update adds context0 and changes the registry hash. The updated helper refuses old firmware during the capability check, before opening a session or sending any context.

Keep the current helper and working UF2 available. Build and review the updated firmware and helper before a separate flash session. After both halves run the matching build, start the new helper and select Auto on the keyboard. This update does not require reimporting a preset. Preserve the current tested comfort layout.

## Test after flashing

1. Close Vial, start the matching helper, and confirm `phase=ready`.
2. Hold Menu and press V to enable Auto. Release both keys. Focus Codex and confirm the OpenAI panel appears.
3. Open Raycast and release the opening shortcut. Wait for KeyPeek to show Typing/layer0, then type a harmless search such as `calculator`. Do not execute it yet.
4. Dismiss Raycast with Escape. Confirm the OpenAI panel returns. Repeat from Claude or a browser and confirm that app's panel returns.
5. Open Raycast again, perform physical Home, then dismiss Raycast. The keyboard must remain in Typing until you deliberately select Auto again.

App activation notifications wake the helper promptly, with a 250ms polling fallback. Switching still waits for all keys and pending tap/hold decisions to finish. A held shortcut or home-row modifier can therefore delay the change. Check the displayed layer before typing during the first tests. There is no guarantee of zero activation latency.

If the helper stops or loses its session while Raycast is selected, the keyboard remains in Typing and disarms Auto. The helper retries a single missed reply, then reconnects automatically after temporary transport failures. A full reconnect does not rearm Auto. When `phase=ready` returns, select Auto again on the keyboard when ready. Typing `pause` prevents automatic recovery until you type `resume`.

## Software verification

The C suite exercises layer0 entry and exit, physical Home, exact context validation, held-key/tapping deferral, session loss, timeout, overflow, and picker cancellation using the pinned QMK event path under UBSan. Swift tests exercise foreground app mappings, separate state readback, old-registry rejection, notification coalescing/removal, and return to the next app through mock transport.

`command-mode-helper dry-run --observe-apps --simulate-auto` reads live foreground bundle IDs but sends reports only to its mock transport. It does not test or modify the real keyboard. The physical checks above remain necessary after an authorized flash.
