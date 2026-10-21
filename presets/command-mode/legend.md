# Corne command-mode legend

Generated from `config/command-mode.json`. Matrix coordinates are row,column, not keycap names. Both halves offer the same command clusters. The original six layers are preserved in baseline16.

Menu is the left outer thumb. Tap toggles numbers after the 200ms double-tap window. Hold200ms opens Picker; release without selection cancels. Double tap performs Home immediately on the second press. In a command panel a single exits to numbers. Home disarms Auto and clears mirror.

| ID | Panel | Picker left position | Automatic application |
|---|---|---|---|
| 0 | Typing | 0,0 | Manual |
| 1 | Numbers | 0,1 | Manual |
| 2 | Symbols | 0,2 | Manual |
| 3 | Maintenance | 0,3 | Manual |
| 4 | Reserved 4 | 0,4 | Manual |
| 5 | Reserved 5 | 0,5 | Manual |
| 6 | Generic commands | 1,0 | Manual |
| 7 | OpenAI desktop | 1,1 | com.openai.codex |
| 8 | Claude | 1,2 | com.anthropic.claudefordesktop |
| 9 | Browser | 1,3 | com.google.Chrome, com.openai.atlas, com.apple.Safari, com.microsoft.edgemac |
| 10 | Editor | 1,4 | com.todesktop.230313mzl4w4u92, com.microsoft.VSCode |
| 11 | Mouse | 1,5 | Manual |
| 12 | Review | 2,0 | Manual |
| 13 | Experiments | 2,1 | Manual |
| 14 | Spare | 2,2 | Manual |
| 15 | Picker | 2,3 | Manual |

Picker2,4 selects Auto. Picker2,5 performs Home. Left/right inner thumbs3,5 and7,5 hold Mirror in command panels and Picker. The right middle thumb keeps its symbols role. Selecting an app panel manually pins it; Auto follows apps only after deliberate Auto selection. Picker15 can be latched deliberately and cancelled by Menu.

## 6: Generic commands

| Left position | Action | Keycode |
|---|---|---|
| 0,0 | Escape | `KC_ESCAPE` |
| 0,1 | Undo | `LGUI(KC_Z)` |
| 0,2 | Cut | `LGUI(KC_X)` |
| 0,3 | Copy | `LGUI(KC_C)` |
| 0,4 | Paste | `LGUI(KC_V)` |
| 0,5 | Find | `LGUI(KC_F)` |
| 1,0 | Shift, hold to select | `KC_LSHIFT` |
| 1,1 | Left | `KC_LEFT` |
| 1,2 | Down | `KC_DOWN` |
| 1,3 | Up | `KC_UP` |
| 1,4 | Right | `KC_RIGHT` |
| 1,5 | Select all | `LGUI(KC_A)` |
| 2,1 | Page up | `KC_PGUP` |
| 2,2 | Page down | `KC_PGDOWN` |
| 2,3 | Next focus | `KC_TAB` |
| 2,4 | Previous focus | `LSFT(KC_TAB)` |
| 2,5 | Home: typing, Auto off | `USER00` |
| 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| 3,5 | Mirror, hold | `USER02` |

## 7: OpenAI desktop

| Left position | Action | Keycode |
|---|---|---|
| 0,0 | Escape | `KC_ESCAPE` |
| 0,1 | Undo | `LGUI(KC_Z)` |
| 0,2 | Cut | `LGUI(KC_X)` |
| 0,3 | Copy | `LGUI(KC_C)` |
| 0,4 | Paste | `LGUI(KC_V)` |
| 0,5 | Find | `LGUI(KC_F)` |
| 1,0 | Shift, hold to select | `KC_LSHIFT` |
| 1,1 | Left | `KC_LEFT` |
| 1,2 | Down | `KC_DOWN` |
| 1,3 | Up | `KC_UP` |
| 1,4 | Right | `KC_RIGHT` |
| 1,5 | Select all | `LGUI(KC_A)` |
| 2,1 | Page up | `KC_PGUP` |
| 2,2 | Page down | `KC_PGDOWN` |
| 2,3 | Next focus | `KC_TAB` |
| 2,4 | Previous focus | `LSFT(KC_TAB)` |
| 2,0 | Microphone shortcut, explicit F18 | `KC_F18` |
| 2,5 | Home: typing, Auto off | `USER00` |
| 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| 3,5 | Mirror, hold | `USER02` |

## 8: Claude

| Left position | Action | Keycode |
|---|---|---|
| 0,0 | Escape | `KC_ESCAPE` |
| 0,1 | Undo | `LGUI(KC_Z)` |
| 0,2 | Cut | `LGUI(KC_X)` |
| 0,3 | Copy | `LGUI(KC_C)` |
| 0,4 | Paste | `LGUI(KC_V)` |
| 0,5 | Find | `LGUI(KC_F)` |
| 1,0 | Shift, hold to select | `KC_LSHIFT` |
| 1,1 | Left | `KC_LEFT` |
| 1,2 | Down | `KC_DOWN` |
| 1,3 | Up | `KC_UP` |
| 1,4 | Right | `KC_RIGHT` |
| 1,5 | Select all | `LGUI(KC_A)` |
| 2,1 | Page up | `KC_PGUP` |
| 2,2 | Page down | `KC_PGDOWN` |
| 2,3 | Next focus | `KC_TAB` |
| 2,4 | Previous focus | `LSFT(KC_TAB)` |
| 2,0 | Dictate in Claude Code, guarded Raycast hook | `LCTL(LALT(LSFT(KC_D)))` |
| 2,5 | Home: typing, Auto off | `USER00` |
| 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| 3,5 | Mirror, hold | `USER02` |

## 9: Browser

| Left position | Action | Keycode |
|---|---|---|
| 0,0 | Escape | `KC_ESCAPE` |
| 0,1 | Undo | `LGUI(KC_Z)` |
| 0,2 | Cut | `LGUI(KC_X)` |
| 0,3 | Copy | `LGUI(KC_C)` |
| 0,4 | Paste | `LGUI(KC_V)` |
| 0,5 | Find | `LGUI(KC_F)` |
| 1,0 | Shift, hold to select | `KC_LSHIFT` |
| 1,1 | Left | `KC_LEFT` |
| 1,2 | Down | `KC_DOWN` |
| 1,3 | Up | `KC_UP` |
| 1,4 | Right | `KC_RIGHT` |
| 1,5 | Select all | `LGUI(KC_A)` |
| 2,1 | Page up | `KC_PGUP` |
| 2,2 | Page down | `KC_PGDOWN` |
| 2,3 | Next focus | `KC_TAB` |
| 2,4 | Previous focus | `LSFT(KC_TAB)` |
| 2,5 | Home: typing, Auto off | `USER00` |
| 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| 3,5 | Mirror, hold | `USER02` |

## 10: Editor

| Left position | Action | Keycode |
|---|---|---|
| 0,0 | Escape | `KC_ESCAPE` |
| 0,1 | Undo | `LGUI(KC_Z)` |
| 0,2 | Cut | `LGUI(KC_X)` |
| 0,3 | Copy | `LGUI(KC_C)` |
| 0,4 | Paste | `LGUI(KC_V)` |
| 0,5 | Find | `LGUI(KC_F)` |
| 1,0 | Shift, hold to select | `KC_LSHIFT` |
| 1,1 | Left | `KC_LEFT` |
| 1,2 | Down | `KC_DOWN` |
| 1,3 | Up | `KC_UP` |
| 1,4 | Right | `KC_RIGHT` |
| 1,5 | Select all | `LGUI(KC_A)` |
| 2,1 | Page up | `KC_PGUP` |
| 2,2 | Page down | `KC_PGDOWN` |
| 2,3 | Next focus | `KC_TAB` |
| 2,4 | Previous focus | `LSFT(KC_TAB)` |
| 2,5 | Home: typing, Auto off | `USER00` |
| 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| 3,5 | Mirror, hold | `USER02` |

## 11: Mouse

| Left position | Action | Keycode |
|---|---|---|
| 0,0 | Slow | `KC_ACL0` |
| 0,1 | Medium | `KC_ACL1` |
| 0,2 | Fast | `KC_ACL2` |
| 0,3 | Left click | `KC_BTN1` |
| 0,4 | Right click | `KC_BTN2` |
| 0,5 | Middle click | `KC_BTN3` |
| 1,0 | Scroll left | `KC_WH_L` |
| 1,1 | Pointer left | `KC_MS_L` |
| 1,2 | Pointer down | `KC_MS_D` |
| 1,3 | Pointer up | `KC_MS_U` |
| 1,4 | Pointer right | `KC_MS_R` |
| 1,5 | Scroll right | `KC_WH_R` |
| 2,0 | Escape | `KC_ESCAPE` |
| 2,1 | Scroll up | `KC_WH_U` |
| 2,2 | Scroll down | `KC_WH_D` |
| 2,3 | Drag, hold | `KC_BTN1` |
| 2,4 | Right click | `KC_BTN2` |
| 2,5 | Home: typing, Auto off | `USER00` |
| 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| 3,5 | Mirror, hold | `USER02` |

## 12: Review

| Left position | Action | Keycode |
|---|---|---|
| 0,0 | Escape | `KC_ESCAPE` |
| 0,1 | Home | `KC_HOME` |
| 0,2 | End | `KC_END` |
| 0,3 | Page up | `KC_PGUP` |
| 0,4 | Page down | `KC_PGDOWN` |
| 0,5 | Find | `LGUI(KC_F)` |
| 1,0 | Shift, hold to select | `KC_LSHIFT` |
| 1,1 | Left | `KC_LEFT` |
| 1,2 | Down | `KC_DOWN` |
| 1,3 | Up | `KC_UP` |
| 1,4 | Right | `KC_RIGHT` |
| 1,5 | Copy | `LGUI(KC_C)` |
| 2,0 | Next focus | `KC_TAB` |
| 2,1 | Previous focus | `LSFT(KC_TAB)` |
| 2,2 | Space | `KC_SPACE` |
| 2,3 | Enter | `KC_ENTER` |
| 2,5 | Home: typing, Auto off | `USER00` |
| 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| 3,5 | Mirror, hold | `USER02` |

## 13: Experiments

| Left position | Action | Keycode |
|---|---|---|
| 0,0 | Escape | `KC_ESCAPE` |
| 0,1 | Undo | `LGUI(KC_Z)` |
| 0,2 | Cut | `LGUI(KC_X)` |
| 0,3 | Copy | `LGUI(KC_C)` |
| 0,4 | Paste | `LGUI(KC_V)` |
| 0,5 | Find | `LGUI(KC_F)` |
| 1,0 | Shift, hold to select | `KC_LSHIFT` |
| 1,1 | Left | `KC_LEFT` |
| 1,2 | Down | `KC_DOWN` |
| 1,3 | Up | `KC_UP` |
| 1,4 | Right | `KC_RIGHT` |
| 1,5 | Select all | `LGUI(KC_A)` |
| 2,1 | Page up | `KC_PGUP` |
| 2,2 | Page down | `KC_PGDOWN` |
| 2,3 | Next focus | `KC_TAB` |
| 2,4 | Previous focus | `LSFT(KC_TAB)` |
| 2,5 | Home: typing, Auto off | `USER00` |
| 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| 3,5 | Mirror, hold | `USER02` |

## 14: Spare

| Left position | Action | Keycode |
|---|---|---|
| 2,5 | Home: typing, Auto off | `USER00` |
| 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| 3,5 | Mirror, hold | `USER02` |

## 15: Picker

| Left position | Action | Keycode |
|---|---|---|
| 0,0 | Typing | `USER04` |
| 0,1 | Numbers | `USER05` |
| 0,2 | Symbols | `USER06` |
| 0,3 | Maintenance | `USER07` |
| 0,4 | Reserved 4 | `USER08` |
| 0,5 | Reserved 5 | `USER09` |
| 1,0 | Generic commands | `USER10` |
| 1,1 | OpenAI desktop | `USER11` |
| 1,2 | Claude | `USER12` |
| 1,3 | Browser | `USER13` |
| 1,4 | Editor | `USER14` |
| 1,5 | Mouse | `USER15` |
| 2,0 | Review | `USER16` |
| 2,1 | Experiments | `USER17` |
| 2,2 | Spare | `USER18` |
| 2,3 | Picker | `USER19` |
| 2,4 | Auto Command | `USER01` |
| 2,5 | Home: typing, Auto off | `USER00` |
| 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| 3,5 | Mirror, hold | `USER02` |

- App panels use standard macOS edit/navigation keys. App-specific behavior still needs physical validation.
- F18 and Claude's guarded Raycast hook are explicit user actions. No helper focus event invokes them.
- The installed ChatGPT app uses com.openai.codex; there is one OpenAI desktop profile.
- Claude Chat versus Code and browser tabs are not distinguished by bundle ID.

Standard shortcuts: [Apple keyboard shortcuts](https://support.apple.com/en-us/102650). No shortcut, microphone, dictation or typing action was executed during generation/tests.
