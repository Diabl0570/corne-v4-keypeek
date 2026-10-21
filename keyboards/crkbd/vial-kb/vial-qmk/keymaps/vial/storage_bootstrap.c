#include "quantum.h"
#include "dynamic_keymap.h"
#include "keymap_introspection.h"
#include "qmk_settings.h"
#include "via.h"
#include "vial.h"
#include "quantum/nvm/nvm_eeconfig.h"
#include "command_settings.h"
#include "storage_bootstrap.h"

#include <string.h>

#if !defined(COMMAND_MODE_ENABLE) || !defined(VIAL_ENABLE) || !defined(QMK_SETTINGS)
#    error "Command mode storage requires Vial and QMK settings"
#endif
#if DYNAMIC_KEYMAP_LAYER_COUNT != 16
#    error "Command mode storage schema requires exactly sixteen layers"
#endif

void command_mode_storage_reset(void) {
    via_eeprom_set_valid(false);
    via_set_layout_options(VIA_EEPROM_LAYOUT_OPTIONS_DEFAULT);

    for (uint8_t layer = 0; layer < DYNAMIC_KEYMAP_LAYER_COUNT; ++layer) {
        for (uint8_t row = 0; row < MATRIX_ROWS; ++row) {
            for (uint8_t col = 0; col < MATRIX_COLS; ++col) {
                dynamic_keymap_set_keycode(layer, row, col, keycode_at_keymap_location_raw(layer, row, col));
            }
        }
#ifdef ENCODER_MAP_ENABLE
        for (uint8_t encoder = 0; encoder < NUM_ENCODERS; ++encoder) {
            dynamic_keymap_set_encoder(layer, encoder, true, keycode_at_encodermap_location_raw(layer, encoder, true));
            dynamic_keymap_set_encoder(layer, encoder, false, keycode_at_encodermap_location_raw(layer, encoder, false));
        }
#endif
    }

    memset(&QS, 0, sizeof(QS));
    for (size_t i = 0; i < ARRAY_SIZE(cm_initial_settings); ++i) {
        /* ID 21 lives in core EEPROM. Keep its existing flags until the explicit Vial import. */
        if (cm_initial_settings[i].id == 21) continue;
        uint32_t value = cm_initial_settings[i].value;
        uint8_t data[] = {value, value >> 8, value >> 16, value >> 24};
        if (qmk_settings_set(cm_initial_settings[i].id, data, sizeof(data)) != 0) {
            /* A generated setting unsupported by this build must never publish a valid image. */
            for (;;) {}
        }
    }

#ifdef VIAL_TAP_DANCE_ENABLE
    vial_tap_dance_entry_t td = {KC_NO, KC_NO, KC_NO, KC_NO, TAPPING_TERM};
    for (uint8_t i = 0; i < VIAL_TAP_DANCE_ENTRIES; ++i) dynamic_keymap_set_tap_dance(i, &td);
#endif
#ifdef VIAL_COMBO_ENABLE
    vial_combo_entry_t combo = {0};
    for (uint8_t i = 0; i < VIAL_COMBO_ENTRIES; ++i) dynamic_keymap_set_combo(i, &combo);
#endif
#ifdef VIAL_KEY_OVERRIDE_ENABLE
    vial_key_override_entry_t ko = {0};
    ko.layers = ~0;
    ko.options = vial_ko_option_activation_negative_mod_up | vial_ko_option_activation_required_mod_down | vial_ko_option_activation_trigger_down;
    for (uint8_t i = 0; i < VIAL_KEY_OVERRIDE_ENTRIES; ++i) dynamic_keymap_set_key_override(i, &ko);
#endif
#ifdef VIAL_ALT_REPEAT_KEY_ENABLE
    vial_alt_repeat_key_entry_t arep = {0};
    for (uint8_t i = 0; i < VIAL_ALT_REPEAT_KEY_ENTRIES; ++i) dynamic_keymap_set_alt_repeat_key(i, &arep);
#endif
    dynamic_keymap_macro_reset();
    via_eeprom_set_valid(true);
}

void command_mode_storage_bootstrap(void) {
    if (!nvm_eeconfig_is_enabled()) {
        via_eeprom_set_valid(false);
        eeconfig_init();
    } else if (!via_eeprom_is_valid()) {
        command_mode_storage_reset();
    }
}
