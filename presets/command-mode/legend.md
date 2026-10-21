# Corne command-mode legend

Generated from `config/command-mode.json`. Matrix coordinates are row,column, not keycap names. Both halves offer the same command clusters. The original six layers are preserved in baseline16.

Menu is the left outer thumb. Tap toggles numbers after the 200ms double-tap window. Hold 200ms opens Picker; release without selection cancels. Double tap performs Home immediately on the second press. In a command panel a single exits to numbers. Home disarms Auto and clears mirror.

| ID | Panel | Left keycap in Picker | Matrix | Automatic application |
|---|---|---|---|---|
| 0 | Typing | Esc | 0,0 | Manual |
| 1 | Numbers | Q | 0,1 | Manual |
| 2 | Symbols | W | 0,2 | Manual |
| 3 | Maintenance | E | 0,3 | Manual |
| 4 | Reserved 4 | R | 0,4 | Manual |
| 5 | Reserved 5 | T | 0,5 | Manual |
| 6 | Generic commands | Tab | 1,0 | Manual |
| 7 | OpenAI desktop | A | 1,1 | com.openai.codex |
| 8 | Claude | S | 1,2 | com.anthropic.claudefordesktop |
| 9 | Browser | D | 1,3 | com.google.Chrome, com.openai.atlas, com.apple.Safari, com.microsoft.edgemac |
| 10 | Editor | F | 1,4 | com.todesktop.230313mzl4w4u92, com.microsoft.VSCode |
| 11 | Mouse | G | 1,5 | Manual |
| 12 | Review | Shift | 2,0 | Manual |
| 13 | Experiments | Z | 2,1 | Manual |
| 14 | Spare | X | 2,2 | Manual |
| 15 | Picker | C | 2,3 | Manual |

In Picker, left V selects Auto and left B performs Home. The inner thumbs hold Mirror in command panels and Picker. The right middle thumb keeps its symbols role. Command clusters are duplicated on both halves, so Mouse provides pointer, scroll, buttons and speed without the right hand. Normal Space stays Space; experimental16 alone changes typing Space to tap Space / hold Mirror. Selecting an app panel manually pins it; Auto follows apps only after deliberate Auto selection. Picker15 can be latched deliberately and cancelled by Menu.

## 6: Generic commands

| Left keycap | Matrix | Action | Keycode |
|---|---|---|---|
| Esc | 0,0 | Escape | `KC_ESCAPE` |
| Q | 0,1 | Undo | `LGUI(KC_Z)` |
| W | 0,2 | Cut | `LGUI(KC_X)` |
| E | 0,3 | Copy | `LGUI(KC_C)` |
| R | 0,4 | Paste | `LGUI(KC_V)` |
| T | 0,5 | Find | `LGUI(KC_F)` |
| Tab | 1,0 | Shift, hold to select | `KC_LSHIFT` |
| A | 1,1 | Left | `KC_LEFT` |
| S | 1,2 | Down | `KC_DOWN` |
| D | 1,3 | Up | `KC_UP` |
| F | 1,4 | Right | `KC_RIGHT` |
| G | 1,5 | Select all | `LGUI(KC_A)` |
| Z | 2,1 | Page up | `KC_PGUP` |
| X | 2,2 | Page down | `KC_PGDOWN` |
| C | 2,3 | Next focus | `KC_TAB` |
| V | 2,4 | Previous focus | `LSFT(KC_TAB)` |
| B | 2,5 | Home: typing, Auto off | `USER00` |
| Menu | 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| Space | 3,5 | Mirror, hold | `USER02` |

## 7: OpenAI desktop

| Left keycap | Matrix | Action | Keycode |
|---|---|---|---|
| Esc | 0,0 | Escape | `KC_ESCAPE` |
| Q | 0,1 | Undo | `LGUI(KC_Z)` |
| W | 0,2 | Cut | `LGUI(KC_X)` |
| E | 0,3 | Copy | `LGUI(KC_C)` |
| R | 0,4 | Paste | `LGUI(KC_V)` |
| T | 0,5 | Find | `LGUI(KC_F)` |
| Tab | 1,0 | Shift, hold to select | `KC_LSHIFT` |
| A | 1,1 | Left | `KC_LEFT` |
| S | 1,2 | Down | `KC_DOWN` |
| D | 1,3 | Up | `KC_UP` |
| F | 1,4 | Right | `KC_RIGHT` |
| G | 1,5 | Select all | `LGUI(KC_A)` |
| Z | 2,1 | Page up | `KC_PGUP` |
| X | 2,2 | Page down | `KC_PGDOWN` |
| C | 2,3 | Next focus | `KC_TAB` |
| V | 2,4 | Previous focus | `LSFT(KC_TAB)` |
| Shift | 2,0 | Microphone shortcut, explicit F18 | `KC_F18` |
| B | 2,5 | Home: typing, Auto off | `USER00` |
| Menu | 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| Space | 3,5 | Mirror, hold | `USER02` |

## 8: Claude

| Left keycap | Matrix | Action | Keycode |
|---|---|---|---|
| Esc | 0,0 | Escape | `KC_ESCAPE` |
| Q | 0,1 | Undo | `LGUI(KC_Z)` |
| W | 0,2 | Cut | `LGUI(KC_X)` |
| E | 0,3 | Copy | `LGUI(KC_C)` |
| R | 0,4 | Paste | `LGUI(KC_V)` |
| T | 0,5 | Find | `LGUI(KC_F)` |
| Tab | 1,0 | Shift, hold to select | `KC_LSHIFT` |
| A | 1,1 | Left | `KC_LEFT` |
| S | 1,2 | Down | `KC_DOWN` |
| D | 1,3 | Up | `KC_UP` |
| F | 1,4 | Right | `KC_RIGHT` |
| G | 1,5 | Select all | `LGUI(KC_A)` |
| Z | 2,1 | Page up | `KC_PGUP` |
| X | 2,2 | Page down | `KC_PGDOWN` |
| C | 2,3 | Next focus | `KC_TAB` |
| V | 2,4 | Previous focus | `LSFT(KC_TAB)` |
| Shift | 2,0 | Dictate in Claude Code, guarded Raycast hook | `LCTL(LALT(LSFT(KC_D)))` |
| B | 2,5 | Home: typing, Auto off | `USER00` |
| Menu | 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| Space | 3,5 | Mirror, hold | `USER02` |

## 9: Browser

| Left keycap | Matrix | Action | Keycode |
|---|---|---|---|
| Esc | 0,0 | Escape | `KC_ESCAPE` |
| Q | 0,1 | Undo | `LGUI(KC_Z)` |
| W | 0,2 | Cut | `LGUI(KC_X)` |
| E | 0,3 | Copy | `LGUI(KC_C)` |
| R | 0,4 | Paste | `LGUI(KC_V)` |
| T | 0,5 | Find | `LGUI(KC_F)` |
| Tab | 1,0 | Shift, hold to select | `KC_LSHIFT` |
| A | 1,1 | Left | `KC_LEFT` |
| S | 1,2 | Down | `KC_DOWN` |
| D | 1,3 | Up | `KC_UP` |
| F | 1,4 | Right | `KC_RIGHT` |
| G | 1,5 | Select all | `LGUI(KC_A)` |
| Z | 2,1 | Page up | `KC_PGUP` |
| X | 2,2 | Page down | `KC_PGDOWN` |
| C | 2,3 | Next focus | `KC_TAB` |
| V | 2,4 | Previous focus | `LSFT(KC_TAB)` |
| B | 2,5 | Home: typing, Auto off | `USER00` |
| Menu | 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| Space | 3,5 | Mirror, hold | `USER02` |

## 10: Editor

| Left keycap | Matrix | Action | Keycode |
|---|---|---|---|
| Esc | 0,0 | Escape | `KC_ESCAPE` |
| Q | 0,1 | Undo | `LGUI(KC_Z)` |
| W | 0,2 | Cut | `LGUI(KC_X)` |
| E | 0,3 | Copy | `LGUI(KC_C)` |
| R | 0,4 | Paste | `LGUI(KC_V)` |
| T | 0,5 | Find | `LGUI(KC_F)` |
| Tab | 1,0 | Shift, hold to select | `KC_LSHIFT` |
| A | 1,1 | Left | `KC_LEFT` |
| S | 1,2 | Down | `KC_DOWN` |
| D | 1,3 | Up | `KC_UP` |
| F | 1,4 | Right | `KC_RIGHT` |
| G | 1,5 | Select all | `LGUI(KC_A)` |
| Z | 2,1 | Page up | `KC_PGUP` |
| X | 2,2 | Page down | `KC_PGDOWN` |
| C | 2,3 | Next focus | `KC_TAB` |
| V | 2,4 | Previous focus | `LSFT(KC_TAB)` |
| B | 2,5 | Home: typing, Auto off | `USER00` |
| Menu | 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| Space | 3,5 | Mirror, hold | `USER02` |

## 11: Mouse

| Left keycap | Matrix | Action | Keycode |
|---|---|---|---|
| Esc | 0,0 | Slow | `KC_ACL0` |
| Q | 0,1 | Medium | `KC_ACL1` |
| W | 0,2 | Fast | `KC_ACL2` |
| E | 0,3 | Left click | `KC_BTN1` |
| R | 0,4 | Right click | `KC_BTN2` |
| T | 0,5 | Middle click | `KC_BTN3` |
| Tab | 1,0 | Scroll left | `KC_WH_L` |
| A | 1,1 | Pointer left | `KC_MS_L` |
| S | 1,2 | Pointer down | `KC_MS_D` |
| D | 1,3 | Pointer up | `KC_MS_U` |
| F | 1,4 | Pointer right | `KC_MS_R` |
| G | 1,5 | Scroll right | `KC_WH_R` |
| Shift | 2,0 | Escape | `KC_ESCAPE` |
| Z | 2,1 | Scroll up | `KC_WH_U` |
| X | 2,2 | Scroll down | `KC_WH_D` |
| C | 2,3 | Drag, hold | `KC_BTN1` |
| V | 2,4 | Right click | `KC_BTN2` |
| B | 2,5 | Home: typing, Auto off | `USER00` |
| Menu | 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| Space | 3,5 | Mirror, hold | `USER02` |

## 12: Review

| Left keycap | Matrix | Action | Keycode |
|---|---|---|---|
| Esc | 0,0 | Escape | `KC_ESCAPE` |
| Q | 0,1 | Home | `KC_HOME` |
| W | 0,2 | End | `KC_END` |
| E | 0,3 | Page up | `KC_PGUP` |
| R | 0,4 | Page down | `KC_PGDOWN` |
| T | 0,5 | Find | `LGUI(KC_F)` |
| Tab | 1,0 | Shift, hold to select | `KC_LSHIFT` |
| A | 1,1 | Left | `KC_LEFT` |
| S | 1,2 | Down | `KC_DOWN` |
| D | 1,3 | Up | `KC_UP` |
| F | 1,4 | Right | `KC_RIGHT` |
| G | 1,5 | Copy | `LGUI(KC_C)` |
| Shift | 2,0 | Next focus | `KC_TAB` |
| Z | 2,1 | Previous focus | `LSFT(KC_TAB)` |
| X | 2,2 | Space | `KC_SPACE` |
| C | 2,3 | Enter | `KC_ENTER` |
| B | 2,5 | Home: typing, Auto off | `USER00` |
| Menu | 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| Space | 3,5 | Mirror, hold | `USER02` |

## 13: Experiments

| Left keycap | Matrix | Action | Keycode |
|---|---|---|---|
| Esc | 0,0 | Escape | `KC_ESCAPE` |
| Q | 0,1 | Undo | `LGUI(KC_Z)` |
| W | 0,2 | Cut | `LGUI(KC_X)` |
| E | 0,3 | Copy | `LGUI(KC_C)` |
| R | 0,4 | Paste | `LGUI(KC_V)` |
| T | 0,5 | Find | `LGUI(KC_F)` |
| Tab | 1,0 | Shift, hold to select | `KC_LSHIFT` |
| A | 1,1 | Left | `KC_LEFT` |
| S | 1,2 | Down | `KC_DOWN` |
| D | 1,3 | Up | `KC_UP` |
| F | 1,4 | Right | `KC_RIGHT` |
| G | 1,5 | Select all | `LGUI(KC_A)` |
| Z | 2,1 | Page up | `KC_PGUP` |
| X | 2,2 | Page down | `KC_PGDOWN` |
| C | 2,3 | Next focus | `KC_TAB` |
| V | 2,4 | Previous focus | `LSFT(KC_TAB)` |
| B | 2,5 | Home: typing, Auto off | `USER00` |
| Menu | 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| Space | 3,5 | Mirror, hold | `USER02` |

## 14: Spare

| Left keycap | Matrix | Action | Keycode |
|---|---|---|---|
| B | 2,5 | Home: typing, Auto off | `USER00` |
| Menu | 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| Space | 3,5 | Mirror, hold | `USER02` |

## 15: Picker

| Left keycap | Matrix | Action | Keycode |
|---|---|---|---|
| Esc | 0,0 | Typing | `USER04` |
| Q | 0,1 | Numbers | `USER05` |
| W | 0,2 | Symbols | `USER06` |
| E | 0,3 | Maintenance | `USER07` |
| R | 0,4 | Reserved 4 | `USER08` |
| T | 0,5 | Reserved 5 | `USER09` |
| Tab | 1,0 | Generic commands | `USER10` |
| A | 1,1 | OpenAI desktop | `USER11` |
| S | 1,2 | Claude | `USER12` |
| D | 1,3 | Browser | `USER13` |
| F | 1,4 | Editor | `USER14` |
| G | 1,5 | Mouse | `USER15` |
| Shift | 2,0 | Review | `USER16` |
| Z | 2,1 | Experiments | `USER17` |
| X | 2,2 | Spare | `USER18` |
| C | 2,3 | Picker | `USER19` |
| V | 2,4 | Auto Command | `USER01` |
| B | 2,5 | Home: typing, Auto off | `USER00` |
| Menu | 3,3 | Menu: tap numbers / hold picker / double Home | `TG(1)` |
| Space | 3,5 | Mirror, hold | `USER02` |

- App panels use standard macOS edit/navigation keys. App-specific behavior still needs physical validation.
- F18 and Claude's guarded Raycast hook are explicit user actions. No helper focus event invokes them.
- The installed ChatGPT app uses com.openai.codex; there is one OpenAI desktop profile.
- Claude Chat versus Code and browser tabs are not distinguished by bundle ID.

Standard shortcuts: [Apple keyboard shortcuts](https://support.apple.com/en-us/102650). No shortcut, microphone, dictation or typing action was executed during generation/tests.
