#include "command_qmk.h"
#include "command_protocol.h"
#include "action_tapping.h"
#include "usb_device_state.h"

enum { CM_PHYSICAL_KEYS = MATRIX_ROWS * MATRIX_COLS, CM_INPUTS = CM_PHYSICAL_KEYS + NUM_ENCODERS * 2 };
enum { CM_LOGICAL_KEYS = CM_PHYSICAL_KEYS + NUM_ENCODERS };
typedef enum { CM_FREE, CM_ORDINARY, CM_MENU_KEY, CM_FN_KEY, CM_MIRROR_KEY, CM_SPACE_KEY, CM_COMMAND_KEY, CM_COLLISION } cm_role_t;
typedef struct {
    cm_role_t role;
    uint32_t generation, pressed_at;
    uint8_t logical;
    bool space_held;
} cm_press_t;

static cm_state_t state;
static cm_protocol_t protocol;
static cm_press_t presses[CM_INPUTS];
static uint8_t logical_owner[CM_LOGICAL_KEYS];
static uint8_t logical_layer[CM_LOGICAL_KEYS];
static uint32_t applied_revision;
static bool initialized;
static usb_configure_state_t usb_state = USB_DEVICE_STATE_NO_INIT;

const keypos_t PROGMEM hand_swap_config[MATRIX_ROWS][MATRIX_COLS] = {
    {{0,4}, {1,4}, {2,4}, {3,4}, {4,4}, {5,4}, {6,4}},
    {{0,5}, {1,5}, {2,5}, {3,5}, {4,5}, {5,5}, {6,5}},
    {{0,6}, {1,6}, {2,6}, {3,6}, {4,6}, {5,6}, {6,6}},
    {{0,7}, {1,7}, {2,7}, {3,3}, {4,7}, {5,7}, {6,7}},
    {{0,0}, {1,0}, {2,0}, {3,0}, {4,0}, {5,0}, {6,0}},
    {{0,1}, {1,1}, {2,1}, {3,1}, {4,1}, {5,1}, {6,1}},
    {{0,2}, {1,2}, {2,2}, {3,2}, {4,2}, {5,2}, {6,2}},
    {{0,3}, {1,3}, {2,3}, {3,7}, {4,3}, {5,3}, {6,3}},
};
const uint8_t PROGMEM encoder_hand_swap_config[NUM_ENCODERS] = {2, 3, 0, 1};

static void initialize(void) {
    if (initialized) return;
    cm_init(&state);
    applied_revision = state.revision;
    initialized = true;
}

static bool all_up(void) {
    for (uint8_t i = 0; i < CM_INPUTS; ++i) if (presses[i].role != CM_FREE) return false;
    return true;
}

static bool quiescent(void) {
    return all_up() && action_tapping_is_idle();
}

static void apply(void) {
    if (state.revision == applied_revision) return;
    if (state.mirror_holds) swap_hands_on();
    else swap_hands_off();
    uint16_t mask = cm_layer_mask(&state);
    if (layer_state != mask) layer_state_set(mask);
    applied_revision = state.revision;
}

static int16_t physical_id(keyevent_t event) {
    if (IS_KEYEVENT(event) && event.key.row < MATRIX_ROWS && event.key.col < MATRIX_COLS) return event.key.row * MATRIX_COLS + event.key.col;
    if (IS_ENCODEREVENT(event) && event.key.col < NUM_ENCODERS) return CM_PHYSICAL_KEYS + event.key.col * 2 + (event.key.row == KEYLOC_ENCODER_CW);
    return -1;
}

static keypos_t logical_position(keyevent_t event) {
    if (!is_swap_hands_on()) return event.key;
    if (IS_KEYEVENT(event)) {
        return (keypos_t){pgm_read_byte(&hand_swap_config[event.key.row][event.key.col].col), pgm_read_byte(&hand_swap_config[event.key.row][event.key.col].row)};
    }
    return (keypos_t){pgm_read_byte(&encoder_hand_swap_config[event.key.col]), event.key.row};
}

static uint8_t logical_id(keypos_t key) {
    return key.row < MATRIX_ROWS ? key.row * MATRIX_COLS + key.col : CM_PHYSICAL_KEYS + key.col;
}

bool command_mode_source_layer(keypos_t key, uint8_t *layer) {
    if (!(key.row < MATRIX_ROWS && key.col < MATRIX_COLS) &&
        !((key.row == KEYLOC_ENCODER_CW || key.row == KEYLOC_ENCODER_CCW) && key.col < NUM_ENCODERS)) return false;
    uint8_t slot = logical_id(key);
    if (!logical_owner[slot]) return false;
    *layer = logical_layer[slot];
    return true;
}

static void expire_owners(void) {
    if (!action_tapping_is_idle()) return;
    for (uint8_t i = 0; i < CM_LOGICAL_KEYS; ++i) {
        if (!logical_owner[i]) continue;
        const cm_press_t *press = &presses[logical_owner[i] - 1];
        if (press->role != CM_ORDINARY || press->logical != i) logical_owner[i] = 0;
    }
}

static void hold_spaces(uint32_t now, bool interrupted) {
    for (uint8_t i = 0; i < CM_INPUTS; ++i) {
        cm_press_t *press = &presses[i];
        if (press->role == CM_SPACE_KEY && !press->space_held && press->generation == state.home_generation &&
            (interrupted || (uint32_t)(now - press->pressed_at) >= CM_GESTURE_MS)) {
            press->space_held = true;
            cm_control(&state, true, true);
        }
    }
}

bool command_mode_pre_action(keyevent_t event) {
    initialize();
    int16_t physical = physical_id(event);
    if (physical < 0) return true;
    uint32_t now = timer_read32();
    expire_owners();
    cm_press_t *press = &presses[physical];
    if (!event.pressed) {
        hold_spaces(now, false);
        cm_role_t role = press->role;
        bool current = press->generation == state.home_generation;
        if (role == CM_MENU_KEY) cm_menu(&state, false, now);
        else if (current && role == CM_FN_KEY) cm_control(&state, false, false);
        else if (current && role == CM_MIRROR_KEY) cm_control(&state, true, false);
        else if (current && role == CM_SPACE_KEY) {
            if (press->space_held) cm_control(&state, true, false);
            else tap_code(KC_SPC);
        }
        *press = (cm_press_t){0};
        apply();
        return role == CM_ORDINARY;
    }
    if (press->role != CM_FREE) return false;
    hold_spaces(now, true);
    bool menu = IS_KEYEVENT(event) && event.key.row == 3 && event.key.col == 3;
    if (!menu) cm_interrupt(&state, now);
    apply();
    keypos_t logical = logical_position(event);
    uint8_t slot = logical_id(logical);
    *press = (cm_press_t){.role = CM_COMMAND_KEY, .generation = state.home_generation, .pressed_at = now};
    if (!menu && logical_owner[slot] && logical_owner[slot] != physical + 1) {
        press->role = CM_COLLISION;
        return false;
    }
    uint8_t layer = layer_switch_get_layer(logical);
    uint16_t keycode = keymap_key_to_keycode(layer, logical);
    if (menu) {
        press->role = CM_MENU_KEY;
        cm_menu(&state, true, now);
    } else if (keycode == CM_HOME) cm_home(&state);
    else if (keycode == CM_AUTO) cm_auto(&state);
    else if (keycode >= CM_SELECT_0 && keycode <= CM_SELECT_LAST) cm_select(&state, keycode - CM_SELECT_0);
    else if (keycode == CM_MIRROR) {
        press->role = CM_MIRROR_KEY;
        cm_control(&state, true, true);
    } else if (keycode == CM_SPACE_MIRROR) press->role = CM_SPACE_KEY;
    else if (keycode == QK_TRI_LAYER_UPPER) {
        press->role = CM_FN_KEY;
        cm_control(&state, false, true);
    } else {
        press->logical = slot;
        logical_layer[slot] = layer;
        logical_owner[slot] = physical + 1;
        press->role = CM_ORDINARY;
    }
    apply();
    return press->role == CM_ORDINARY;
}

void command_mode_housekeeping(void) {
    initialize();
    uint32_t now = timer_read32();
    hold_spaces(now, false);
    cm_tick(&state, now, quiescent());
    expire_owners();
    apply();
}

bool command_mode_handle_report(uint8_t *data, uint8_t length) {
    initialize();
    bool handled = cm_report(&protocol, &state, data, length, timer_read32(), quiescent());
    apply();
    return handled;
}

void command_mode_configuration_activity(void) {
    initialize();
    cm_configuration(&state, timer_read32());
    apply();
}

void notify_usb_device_state_change_user(struct usb_device_state device) {
    if (usb_state == device.configure_state) return;
    usb_state = device.configure_state;
    if (usb_state == USB_DEVICE_STATE_CONFIGURED) return;
    initialize();
    cm_session_lost(&state);
    apply();
}

const cm_state_t *command_mode_state(void) {
    initialize();
    return &state;
}
