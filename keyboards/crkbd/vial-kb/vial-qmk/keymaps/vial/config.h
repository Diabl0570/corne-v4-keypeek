#pragma once

// RGB Matrix already synchronizes its preferences via RGB_MATRIX_SPLIT.
// Also send both layer_state and default_layer_state to the other half.
#define SPLIT_LAYER_STATE_ENABLE

#define VIAL_KEYBOARD_UID {0x89, 0x36, 0x2A, 0xC7, 0xFA, 0xD8, 0x89, 0x45}
#define VIAL_UNLOCK_COMBO_ROWS {0, 0}
#define VIAL_UNLOCK_COMBO_COLS {0, 1}

// vial-qmk has no raw_hid_receive_user, so the module's built-in handler
// does not compile. We install the handler ourselves in keymap.c.
#define KEYPEEK_DISABLE_RAW_HID_HANDLER

// The custom RGB Matrix output adapter retains the stock WS2812 vendor driver.
#define WS2812_LED_COUNT RGB_MATRIX_LED_COUNT

#ifdef COMMAND_MODE_ENABLE
#    undef DYNAMIC_KEYMAP_LAYER_COUNT
#    define DYNAMIC_KEYMAP_LAYER_COUNT 16
#    undef PRODUCT
#    define PRODUCT "Corne v4 CM1"
#    undef DEVICE_VER
#    define DEVICE_VER 0x0411
#endif
