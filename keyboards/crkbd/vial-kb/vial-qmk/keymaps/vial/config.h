#pragma once

#define VIAL_KEYBOARD_UID {0x89, 0x36, 0x2A, 0xC7, 0xFA, 0xD8, 0x89, 0x45}
#define VIAL_UNLOCK_COMBO_ROWS {0, 0}
#define VIAL_UNLOCK_COMBO_COLS {0, 1}

// vial-qmk has no raw_hid_receive_user, so the module's built-in handler
// does not compile. We install the handler ourselves in keymap.c.
#define KEYPEEK_DISABLE_RAW_HID_HANDLER
