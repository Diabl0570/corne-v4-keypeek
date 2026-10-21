#pragma once

#include QMK_KEYBOARD_H
#include "command_state.h"

enum {
    CM_HOME = QK_KB_0,
    CM_AUTO,
    CM_MIRROR,
    CM_SPACE_MIRROR,
    CM_SELECT_0,
    CM_SELECT_LAST = CM_SELECT_0 + 15
};

void command_mode_post_record(keyrecord_t *record);
bool command_mode_process_record(uint16_t keycode, keyrecord_t *record);
bool command_mode_pre_action(keyevent_t event);
bool command_mode_source_layer(keypos_t key, uint8_t *layer);
bool command_mode_handle_report(uint8_t *data, uint8_t length);
void command_mode_configuration_activity(void);
void command_mode_housekeeping(void);
const cm_state_t *command_mode_state(void);
