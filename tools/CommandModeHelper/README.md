# Command-mode helper

This native macOS helper observes foreground bundle IDs and supplies context to supported Corne firmware. Select Auto Command on the keyboard to permit app changes. Typing, Home, manual panels, and picker authority remain in firmware. The helper cannot arm Auto or send a layer-selection command.

## Build and check

Requires macOS 13 or later and Swift 6. Run from this directory.

```sh
swift test
swift build -c release
python3 verify_cli.py
.build/release/command-mode-helper --help
.build/release/command-mode-helper dry-run --observe-apps --seconds 8
```

The dry-run branch constructs `MockReportTransport` directly. It does not call native discovery, open a device, or send HID reports. `--observe-apps` reads foreground and running app bundle IDs through `NSWorkspace`, plus window metadata to detect Raycast's visible search panel. It reads only owner PID, on-screen status, layer, alpha and bounds; it does not inspect titles, pixels, Accessibility content, microphone state, or browser tabs, and it does not request Accessibility or Screen Recording permission. `--simulate-auto` models a deliberate keyboard Auto selection in the mock, after the new session has started disarmed.

`Sources/CommandModeCore/Registry.generated.swift` comes from the repository registry generator. Regenerate it from the repository root through `python3 tools/command_mode_assets.py generate`. Verify it with `python3 tools/command_mode_assets.py check`. Do not edit generated bundle IDs or layer numbers here.

## Start and status

After supported firmware has been explicitly installed and verified, start in a terminal.

```sh
.build/release/command-mode-helper status
.build/release/command-mode-helper run
```

`status` enumerates the target interface and checks capabilities. It does not open a firmware session or renew another client's lease. It exits with a nonzero status if the firmware is unsupported. On an old descriptor it sends zero output reports.

`run` opens a fresh session, verifies its disarmed state, then polls every 250 ms. The firmware lease lasts two seconds. Select Auto Command on the keyboard after every start, resume, or full reconnect. Home disarms Auto immediately. A new session pins the last panel and disarms Auto.

One missed acknowledgement is retried once with the identical request ID and bytes. This can preserve an otherwise healthy session. If both attempts fail, or a transport error occurs, the helper closes the connection and retries discovery after 0.5, 1, 2, 4, then at most 8 seconds between attempts. Starting without the keyboard also waits and reconnects. A successful state poll resets this backoff. Reconnection checks the descriptor and capabilities again and starts a fresh, disarmed session; it never selects Auto for you.

`phase=retrying` means the helper is waiting to reconnect. `phase=ready` means the connection is established; hold Menu and press V if you want Auto again. A firmware mismatch, invalid reply, contradictory readback, or permission error becomes `phase=blocked` instead of retrying forever. Correct that problem, then type `resume`. Use `pause` to stop recovery attempts or `quit` to exit.

Only the exact descriptor is admitted before the first capability request.

| Field | Required value |
| --- | --- |
| Vendor / product | `0x4653` / `0x0004` |
| Usage page / usage | `0xFF60` / `0x61` |
| Product string | `Corne v4 CM1` |
| Device release | `0x0411` |

Capability acknowledgement must match wire version 1, the 16-layer count, mask width, `0x0F` capabilities, exact Vial UID, schema `0x434D0001`, and generated registry hash. Requests and replies contain exactly 32 bytes. IOHID opens with `kIOHIDOptionsTypeNone`, without seizing the device. The helper never sends KeyPeek C0 subscribe, keepalive, or unsubscribe commands. Incoming Vial and KeyPeek report families are ignored. One request is outstanding at a time, with a 400 ms acknowledgement deadline per attempt and a bounded 64-report receive loop. An unfinished native output prevents a second send and causes reconnect instead. Context acknowledgements require separate state readback. Deferred contexts remain deferred until firmware reports their application.

## Pause, disable, quit, and uninstall

While `run` is active, enter one of these commands followed by Return.

| Command | Effect |
| --- | --- |
| `status` | Print the last verified firmware state and helper phase. |
| `pause` | Send a best-effort CLOSE, disarm the session, and release the handle. |
| `disable` | Same as pause. Keep the helper disabled until explicit resume or quit. |
| `resume` | Negotiate a fresh disarmed session. Select Auto again on the keyboard. |
| `quit` or `q` | Close the session, release the handle, and exit. |

Ctrl-C and SIGTERM also quit through session cleanup. After a crash or forced termination, firmware disarms at lease expiry. No LaunchAgent, startup item, service, persistent preference, or installation step exists. To uninstall a copied binary, quit it and remove that copy. To remove build products, delete this directory's `.build` folder. The source checkout can remain.

Running native Vial, bundle `today.vial`, pauses the helper even if Vial is in the background. After Vial quits, the helper waits at least two seconds before reconnecting. Firmware `BUSY_CONFIGURATION` also releases the handle and waits at least two seconds before retrying. Repeated configuration traffic keeps it waiting. These automatic pauses do not override a deliberate `pause` or `disable`: those remain paused until `resume`. For browser configurators or other configuration software, issue `pause` before opening or editing the keyboard. The firmware admission hook remains the authority when other configuration traffic appears.

Recovery does not download updates or flash firmware. It runs the same binary and rechecks compatibility on every connection.

## App matching and action limits

The generated registry maps `com.openai.codex` to OpenAI desktop, Claude's desktop bundle to Claude, supported browsers to Browser, and Cursor/VS Code to Editor. Unknown apps map to Generic. KeyPeek, the system switcher identities, and the helper retain the previous eligible app. These observations cause context reports only while firmware reports an active Auto grant with the current session and epoch. The picker suspends updates. Context changes coalesce to the newest observation and carry a strictly increasing sequence.

Raycast's search panel can receive typing while `NSWorkspace` still reports the underlying app. The helper therefore checks for an on-screen window owned by a currently running Raycast PID, at the modal-panel window level, with positive finite alpha and positive finite bounds. That panel, or genuinely foreground Raycast Settings, temporarily requests Typing layer0. The underlying app identity is retained and refreshed separately. Dismissal restores that app even if focus passes through KeyPeek, Dock, or no reported foreground app. A cold start without an underlying app falls back to Generic. Ordinary background Settings windows and a running Raycast process alone do not trigger the override.

Nonactivating panel entry and dismissal use the existing 250ms polling loop; they do not emit the app-activation notifications that wake ordinary app switching. Layer0 transitions still wait for held keys and tap/hold decisions, so check the displayed layer before typing. Diagnostics distinguish the raw foreground bundle, `raycastPanel=true/false`, and requested context. If window metadata is unavailable, or Raycast changes its window level, panel detection may fail; genuinely foreground Raycast remains supported. No window content or focus-control API is used.

Bundle identity cannot identify browser tabs or distinguish Claude Chat from its Code composer. The helper has no voice, dictation, typing, shortcut, app-control, or Accessibility action path. `capability <action>` exits with an explicit unsupported error. ChatGPT's F18 binding and guarded external Claude dictation hooks remain separate keyboard actions. No hook is invoked by app focus.

The helper supplies no optional overlay. Firmware high-layer behavior, gesture handling, and coexistence with KeyPeek/Vial require the later authorized hardware verification. The tests exercise actual client and codec code with a deterministic mock; they do not establish physical HID compatibility.

## Raycast typing update

Use the matching firmware and helper together. The updated registry hash is checked before opening a session, so this helper refuses the older firmware instead of sending an unsupported layer0 context. Keep the existing helper available until both halves have the matching firmware. No preset reimport is needed for this change; the current typing keys and home-row mods are reused. See [the Raycast test steps](../../docs/raycast-typing.md).
