#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <setjmp.h>

#define COMMAND_MODE_ENABLE
#define EEPROM_DRIVER
#define VIA_ENABLE
#define VIAL_ENABLE
#define QMK_SETTINGS
#define ENCODER_ENABLE
#define ENCODER_MAP_ENABLE
#define VIAL_TAP_DANCE_ENABLE
#define VIAL_COMBO_ENABLE
#define VIAL_KEY_OVERRIDE_ENABLE
#define VIAL_ALT_REPEAT_KEY_ENABLE
#define MOUSEKEY_ENABLE
#define RGB_MATRIX_ENABLE
#define DYNAMIC_KEYMAP_LAYER_COUNT 16
#define MATRIX_ROWS 8
#define MATRIX_COLS 7
#define NUM_ENCODERS 4
#define TOTAL_EEPROM_BYTE_COUNT 8192
#define VIAL_TAP_DANCE_ENTRIES 32
#define VIAL_COMBO_ENTRIES 32
#define VIAL_KEY_OVERRIDE_ENTRIES 32
#define VIAL_ALT_REPEAT_KEY_ENTRIES 32
#define VIA_EEPROM_LAYOUT_OPTIONS_SIZE 1
#define VIA_EEPROM_CUSTOM_CONFIG_SIZE 0
#define VIA_EEPROM_LAYOUT_OPTIONS_DEFAULT 0
#define EECONFIG_KB_DATA_SIZE 0
#define EECONFIG_USER_DATA_SIZE 0
#define EECONFIG_MAGIC_NUMBER 0xFEE3
#define TAPPING_TERM 200
#define TAPPING_TOGGLE 5
#define QK_BOOT 0x7C00
#define AUTO_SHIFT_TIMEOUT 175
#define COMBO_TERM 50
#define MOUSEKEY_DELAY 100
#define MOUSEKEY_INTERVAL 20
#define MOUSEKEY_MOVE_DELTA 8
#define MOUSEKEY_MAX_SPEED 10
#define MOUSEKEY_TIME_TO_MAX 30
#define MOUSEKEY_WHEEL_DELAY 100
#define MOUSEKEY_WHEEL_INTERVAL 80
#define MOUSEKEY_WHEEL_MAX_SPEED 8
#define MOUSEKEY_WHEEL_TIME_TO_MAX 40
#define KC_NO 0
#define PROGMEM
#define PACKED __attribute__((packed))
#define STATIC_ASSERT _Static_assert
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define pgm_read_ptr(p) (*(p))
#define pgm_read_byte(p) (*(const uint8_t *)(p))
#define pgm_read_word(p) (*(const uint16_t *)(p))
#define AUTO_SHIFT_ALPHA 1
#define AUTO_SHIFT_NUMERIC 2
#define AUTO_SHIFT_SPECIAL 3
#define NKRO_DEFAULT_ON false
#define CHORDAL_HOLD
#define IS_NOEVENT(e) ((e).type == 0)

typedef uint16_t layer_state_t;
typedef struct { uint8_t col, row; } keypos_t;
typedef struct { uint8_t type; } keyevent_t;
typedef struct { keyevent_t event; } keyrecord_t;
typedef struct { uint16_t unused; } combo_t;
typedef union {
    uint16_t raw;
    struct {
        uint16_t swap_control_capslock:1, capslock_to_control:1, swap_lalt_lgui:1, swap_ralt_rgui:1;
        uint16_t no_gui:1, swap_grave_esc:1, swap_backslash_backspace:1, nkro:1;
        uint16_t swap_lctl_lgui:1, swap_rctl_rgui:1, oneshot_enable:1, swap_escape_capslock:1, autocorrect_enable:1;
    };
} keymap_config_t;
typedef struct { uint8_t raw; } debug_config_t;
static int vial_unlocked;
static keymap_config_t keymap_config;
static debug_config_t debug_config;
static layer_state_t default_layer_state, layer_state;
static uint16_t mk_delay, mk_interval, mk_max_speed, mk_time_to_max, mk_wheel_delay, mk_wheel_interval, mk_wheel_max_speed, mk_wheel_time_to_max;
#include "vial_types.inc"
#include "core_offsets.inc"
#include "via_offsets.inc"
#include "qmk_settings.h"
#include "command_settings.h"

enum { vial_ko_option_activation_trigger_down = 1, vial_ko_option_activation_required_mod_down = 2, vial_ko_option_activation_negative_mod_up = 4 };
static uint8_t image[TOTAL_EEPROM_BYTE_COUNT];
static bool driver_ready;
static size_t writes, fail_at;
static jmp_buf power_loss;
static bool via_eeprom_is_valid(void);
static void via_eeprom_set_valid(bool valid);
static void via_set_layout_options(uint32_t value);
static void eeconfig_init(void);
static void eeconfig_enable(void);
static bool eeconfig_is_enabled(void);
static void command_mode_storage_reset(void);
void qmk_settings_init(void);

static size_t address_of(const void *address) {
    size_t offset = (uintptr_t)address;
    assert(driver_ready && offset < sizeof(image));
    return offset;
}
static uint8_t eeprom_read_byte(const void *address) { return image[address_of(address)]; }
static void eeprom_update_byte(void *address, uint8_t value) {
    size_t offset = address_of(address);
    if (image[offset] == value) return;
    if (offset >= VIA_EEPROM_LAYOUT_OPTIONS_ADDR) assert(!via_eeprom_is_valid());
    if (writes == fail_at) longjmp(power_loss, 1);
    ++writes;
    image[offset] = value;
}
static uint16_t eeprom_read_word(const void *address) {
    return eeprom_read_byte(address) | ((uint16_t)eeprom_read_byte(address + 1) << 8);
}
static void eeprom_update_word(void *address, uint16_t value) {
    eeprom_update_byte(address, value);
    eeprom_update_byte(address + 1, value >> 8);
}
static void eeprom_read_block(void *data, const void *address, size_t size) {
    for (size_t i = 0; i < size; ++i) ((uint8_t *)data)[i] = eeprom_read_byte(address + i);
}
static void eeprom_update_block(const void *data, void *address, size_t size) {
    for (size_t i = 0; i < size; ++i) eeprom_update_byte(address + i, ((const uint8_t *)data)[i]);
}
#define eeprom_write_block eeprom_update_block
static void nvm_eeconfig_erase(void) {
    for (size_t i = 0; i < sizeof(image); ++i) eeprom_update_byte((void *)i, 0xFF);
}
#include "core_nvm.inc"
static void clear_keyboard(void) {}
static void set_autoshift_timeout(uint16_t value) { (void)value; }
static bool is_flow_tap_key(uint16_t keycode) { return keycode != 0; }
static bool get_chordal_hold_default(keyrecord_t *a, keyrecord_t *b) { return a == b; }
static void eeconfig_update_keymap(const keymap_config_t *value) { eeprom_update_word(EECONFIG_KEYMAP, value->raw); }
static void eeconfig_read_keymap(keymap_config_t *value) { value->raw = eeprom_read_word(EECONFIG_KEYMAP); }
static void eeconfig_update_debug(const debug_config_t *value) { eeprom_update_byte(EECONFIG_DEBUG, value->raw); }
static void eeconfig_read_debug(debug_config_t *value) { value->raw = eeprom_read_byte(EECONFIG_DEBUG); }
static void eeconfig_update_default_layer(layer_state_t value) { eeprom_update_byte(EECONFIG_DEFAULT_LAYER, value); }
static layer_state_t eeconfig_read_default_layer(void) { return eeprom_read_byte(EECONFIG_DEFAULT_LAYER); }
static void eeconfig_init_kb(void) {}
static void eeconfig_update_rgb_matrix_default(void) {
    uint64_t rgb = 0x123456789abcdef0ULL;
    eeprom_update_block(&rgb, EECONFIG_RGB_MATRIX, sizeof(rgb));
}
static void eeconfig_force_flush_rgb_matrix(void) {}
static void via_init_kb(void) {}
static void via_set_layout_options_kb(uint32_t value) { (void)value; }
static void default_layer_set(layer_state_t value) { default_layer_state = value; }
static layer_state_t layer_state_set_kb(layer_state_t value) { return value; }

#include "nvm.inc"
#include "dynamic.inc"
#define qmk_settings_init real_qmk_settings_init
#include "settings.inc"
#undef qmk_settings_init
#include "via.inc"
#include "core.inc"

static uint16_t keycode_at_keymap_location_raw(uint8_t layer, uint8_t row, uint8_t col) {
    return 0x1000 + layer * 0x100 + row * 8 + col;
}
static uint16_t keycode_at_encodermap_location_raw(uint8_t layer, uint8_t encoder, bool clockwise) {
    return 0x3000 + layer * 16 + encoder * 2 + clockwise;
}
#include "storage_bootstrap.c"

void qmk_settings_init(void) {
    assert(via_eeprom_is_valid());
    real_qmk_settings_init();
    for (size_t i = 0; i < ARRAY_SIZE(cm_initial_settings); ++i) {
        if (cm_initial_settings[i].id == 21) continue;
        uint32_t value = 0;
        assert(qmk_settings_get(cm_initial_settings[i].id, &value, sizeof(value)) == 0);
        assert(value == cm_initial_settings[i].value);
    }
}
static void reload_tap_dance(void) {
    assert(via_eeprom_is_valid());
    for (uint8_t i = 0; i < VIAL_TAP_DANCE_ENTRIES; ++i) {
        vial_tap_dance_entry_t td;
        assert(nvm_dynamic_keymap_get_tap_dance(i, &td) == 0);
        assert(td.on_tap == KC_NO && td.on_hold == KC_NO && td.on_double_tap == KC_NO && td.on_tap_hold == KC_NO);
        assert(td.custom_tapping_term == TAPPING_TERM);
    }
}
static void reload_combo(void) { assert(via_eeprom_is_valid()); }
static void reload_key_override(void) { assert(via_eeprom_is_valid()); }
static void reload_alt_repeat_key(void) { assert(via_eeprom_is_valid()); }
#include "vial.inc"
static void print_set_sendchar(void (*send)(char)) { (void)send; }
static void sendchar(char value) { (void)value; }
static void eeprom_driver_init(void) { driver_ready = true; }
static void matrix_setup(void) { assert(via_eeprom_is_valid()); }
static void keyboard_pre_init_quantum(void) { assert(via_eeprom_is_valid()); }
#include "boot.inc"

static keyrecord_t tapping_key;
static uint8_t waiting_buffer_head, waiting_buffer_tail, num_registered_taps;
#include "idle.inc"
static unsigned configuration_count;
void command_mode_configuration_activity(void) { ++configuration_count; }
#include "admission.inc"


#define MAX_LAYER 16
#define ACTION_TRANSPARENT 0xFFFF
typedef struct { uint16_t code; } action_t;
static uint16_t actions[MAX_LAYER][MATRIX_ROWS][MATRIX_COLS];
static unsigned action_lookups;
static bool source_owned;
static uint8_t source_layer;
static action_t action_for_key(uint8_t layer, keypos_t key) {
    ++action_lookups;
    return (action_t){actions[layer][key.row][key.col]};
}
bool command_mode_source_layer(keypos_t key, uint8_t *layer) {
    if (!source_owned || key.row != 0 || key.col != 0) return false;
    *layer = source_layer;
    return true;
}
#include "layer.inc"
#undef COMMAND_MODE_ENABLE
#define layer_switch_get_layer stock_layer_switch_get_layer
#include "layer.inc"
#undef layer_switch_get_layer
#define COMMAND_MODE_ENABLE

static void exercise_source_layer(void) {
    memset(actions, 0xFF, sizeof(actions));
    layer_state = (layer_state_t)1 << 7;
    default_layer_state = 1;
    actions[7][0][0] = 0x0004;
    actions[0][0][0] = 0x2004;
    source_owned = true;
    source_layer = 0;
    action_lookups = 0;
    assert(layer_switch_get_layer((keypos_t){0, 0}) == 0);
    assert(action_lookups == 0);
    assert(stock_layer_switch_get_layer((keypos_t){0, 0}) == 7);
    assert(action_lookups == 1);
    source_owned = false;
    assert(layer_switch_get_layer((keypos_t){0, 0}) == 7);
    actions[7][0][0] = ACTION_TRANSPARENT;
    assert(layer_switch_get_layer((keypos_t){0, 0}) == 0);
    actions[0][0][0] = ACTION_TRANSPARENT;
    assert(layer_switch_get_layer((keypos_t){0, 0}) == 0);
    puts("Actual source-layer hook preserves press ownership before lookup; unowned and non-command builds retain stock search");
}

static void reboot(void) {
    driver_ready = false;
    memset(&QS, 0xA5, sizeof(QS));
    memset(&keymap_config, 0xA5, sizeof(keymap_config));
    keyboard_setup();
    via_init();
    quantum_init();
    assert(via_eeprom_is_valid() && nvm_eeconfig_is_enabled());
}
static void assert_seed(void) {
    for (uint8_t layer = 0; layer < DYNAMIC_KEYMAP_LAYER_COUNT; ++layer) {
        for (uint8_t row = 0; row < MATRIX_ROWS; ++row) {
            for (uint8_t col = 0; col < MATRIX_COLS; ++col) {
                assert(nvm_dynamic_keymap_read_keycode(layer, row, col) == keycode_at_keymap_location_raw(layer, row, col));
            }
        }
        for (uint8_t encoder = 0; encoder < NUM_ENCODERS; ++encoder) {
            for (uint8_t clockwise = 0; clockwise < 2; ++clockwise) {
                assert(nvm_dynamic_keymap_read_encoder(layer, encoder, clockwise) == keycode_at_encodermap_location_raw(layer, encoder, clockwise));
            }
        }
    }
    for (size_t i = DYNAMIC_KEYMAP_MACRO_EEPROM_ADDR; i < sizeof(image); ++i) assert(image[i] == 0);
    reload_tap_dance();
}
static void exercise_power_loss(bool valid_core) {
    uint8_t original[sizeof(image)], expected[sizeof(image)];
    memset(original, 0xFF, sizeof(original));
    if (valid_core) {
        for (size_t i = 0; i < sizeof(original); ++i) original[i] = (uint8_t)(i * 37 + 11);
        original[(uintptr_t)EECONFIG_MAGIC] = EECONFIG_MAGIC_NUMBER & 0xFF;
        original[(uintptr_t)EECONFIG_MAGIC + 1] = EECONFIG_MAGIC_NUMBER >> 8;
    }
    memcpy(image, original, sizeof(image));
    writes = 0;
    fail_at = SIZE_MAX;
    reboot();
    assert_seed();
    if (valid_core) assert(memcmp(image, original, EECONFIG_SIZE) == 0);
    memcpy(expected, image, sizeof(image));
    size_t total = writes;
    writes = 0;
    reboot();
    assert(writes == 0 && memcmp(image, expected, sizeof(image)) == 0);
    for (size_t cut = 0; cut < total; ++cut) {
        memcpy(image, original, sizeof(image));
        writes = 0;
        fail_at = cut;
        if (setjmp(power_loss) == 0) {
            reboot();
            assert(false && "Power-loss boundary was not reached");
        }
        fail_at = SIZE_MAX;
        writes = 0;
        reboot();
        assert(memcmp(image, expected, sizeof(image)) == 0);
        if (valid_core) assert(memcmp(image, original, EECONFIG_SIZE) == 0);
    }
    printf("%s core: %zu interrupted byte writes converged; repeated boot wrote zero bytes\n", valid_core ? "Existing" : "Blank", total);
}
int main(void) {
    exercise_power_loss(true);
    exercise_power_loss(false);
    exercise_source_layer();
    assert(action_tapping_is_idle());
    tapping_key.event.type = 1;
    assert(!action_tapping_is_idle());
    tapping_key.event.type = 0;
    waiting_buffer_head = 1;
    assert(!action_tapping_is_idle());
    waiting_buffer_tail = 1;
    num_registered_taps = 1;
    assert(!action_tapping_is_idle());
    num_registered_taps = 0;
    assert(action_tapping_is_idle());
    uint8_t report[32] = {0xC0};
    admission_fixture(report, sizeof(report));
    report[0] = 0xD3;
    admission_fixture(report, sizeof(report));
    admission_fixture(report, 0);
    assert(configuration_count == 0);
    report[0] = 0xFE;
    admission_fixture(report, sizeof(report));
    report[0] = 0x01;
    admission_fixture(report, sizeof(report));
    assert(configuration_count == 2);
    puts("Actual pinned boot/settings/EEPROM code, later VIA/core initialization, tapping idle, and admission hook passed");
    return 0;
}
