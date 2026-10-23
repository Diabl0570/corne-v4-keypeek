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

The dry-run branch constructs `MockReportTransport` directly. It does not call native discovery, open a device, or send HID reports. `--observe-apps` reads only foreground and running app bundle IDs through `NSWorkspace`. It does not read windows, Accessibility content, microphone state, or browser tabs. `--simulate-auto` models a deliberate keyboard Auto selection in the mock, after the new session has started disarmed.

`Sources/CommandModeCore/Registry.generated.swift` comes from the repository registry generator. Regenerate it from the repository root through `python3 tools/command_mode_assets.py generate`. Verify it with `python3 tools/command_mode_assets.py check`. Do not edit generated bundle IDs or layer numbers here.

## Start and status

After supported firmware has been explicitly installed and verified, start in a terminal.

```sh
.build/release/command-mode-helper status
.build/release/command-mode-helper run
```

`status` enumerates the target interface and checks capabilities. It does not open a firmware session or renew another client's lease. It exits with a nonzero status if the firmware is unsupported. On an old descriptor it sends zero output reports.

`run` opens a fresh session, verifies its disarmed state, then polls every 250 ms. The firmware lease lasts two seconds. Select Auto Command on the keyboard after every start or resume. Home disarms Auto immediately. A lost connection or failed request releases the handle and requires an explicit `resume`. Resume performs fresh passive discovery and revalidates the replacement descriptor before opening it. A new session pins the last panel and disarms Auto.

Only the exact descriptor is admitted before the first capability request.

| Field | Required value |
| --- | --- |
| Vendor / product | `0x4653` / `0x0004` |
| Usage page / usage | `0xFF60` / `0x61` |
| Product string | `Corne v4 CM1` |
| Device release | `0x0411` |

Capability acknowledgement must match wire version 1, the 16-layer count, mask width, `0x0F` capabilities, exact Vial UID, schema `0x434D0001`, and generated registry hash. Requests and replies contain exactly 32 bytes. IOHID opens with `kIOHIDOptionsTypeNone`, without seizing the device. The helper never sends KeyPeek C0 subscribe, keepalive, or unsubscribe commands. Incoming Vial and KeyPeek report families are ignored. One request is outstanding at a time, with a 400 ms acknowledgement deadline and a bounded 64-report receive loop. Context acknowledgements require separate state readback. Deferred contexts remain deferred until firmware reports their application.

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

Running native Vial, bundle `today.vial`, pauses the helper even if Vial is in the background. Quitting Vial does not resume it. Firmware `BUSY_CONFIGURATION` also pauses and releases the handle. Wait until configuration is complete and explicitly resume. For browser configurators or other configuration software, issue `pause` before opening or editing the keyboard. The firmware admission hook remains the authority when other configuration traffic appears.

## App matching and action limits

The generated registry maps `com.openai.codex` to OpenAI desktop, Claude's desktop bundle to Claude, supported browsers to Browser, and Cursor/VS Code to Editor. Unknown apps map to Generic. Raycast selects the existing Typing layer0 while keeping Auto armed. Dismissing Raycast follows the next foreground app. KeyPeek, the system switcher identities, and the helper retain the previous eligible app. These observations cause context reports only while firmware reports an active Auto grant with the current session and epoch. The picker suspends updates. Layer0 transitions use the same held-key/tapping deferral as app panels. NSWorkspace activation notifications wake the single polling loop promptly; callbacks never send HID requests. The 250ms poll remains a fallback. Context changes coalesce to the newest observation and carry a strictly increasing sequence.

Bundle identity cannot identify browser tabs or distinguish Claude Chat from its Code composer. The helper has no voice, dictation, typing, shortcut, app-control, or Accessibility action path. `capability <action>` exits with an explicit unsupported error. ChatGPT's F18 binding and guarded external Claude dictation hooks remain separate keyboard actions. No hook is invoked by app focus.

The helper supplies no optional overlay. Firmware high-layer behavior, gesture handling, and coexistence with KeyPeek/Vial require the later authorized hardware verification. The tests exercise actual client and codec code with a deterministic mock; they do not establish physical HID compatibility.

## Raycast typing update

Use the matching firmware and helper together. The updated registry hash is checked before opening a session, so this helper refuses the older firmware instead of sending an unsupported layer0 context. Keep the existing helper available until both halves have the matching firmware. No preset reimport is needed for this change; the current typing keys and home-row mods are reused. See [the Raycast test steps](../../docs/raycast-typing.md).
