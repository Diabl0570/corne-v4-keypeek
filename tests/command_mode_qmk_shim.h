#ifndef COMMAND_MODE_QMK_SHIM_H
#define COMMAND_MODE_QMK_SHIM_H

#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include "keycodes.h"
#include "action_code.h"

#define MATRIX_ROWS 8
#define MATRIX_COLS 7
#define NUM_ENCODERS 4
#define MAX_LAYER_BITS 4
#define MAX_LAYER 16
#define ENCODER_MAP_ENABLE
#define SWAP_HANDS_ENABLE
#define COMMAND_MODE_ENABLE
#define NO_ACTION_ONESHOT
#define PROGMEM
#define QMK_KEYBOARD_H "command_mode_qmk_shim.h"
#define pgm_read_byte(p) (*(const uint8_t *)(p))
#define TIMER_DIFF_16(a, b) ((uint16_t)((a) - (b)))
#define ac_dprintf(...) ((void)0)
#define debug_event(...) ((void)0)
#define debug_record(...) ((void)0)
#define debug_action(...) ((void)0)
#define dprintln(...) ((void)0)
#define layer_debug(...) ((void)0)
#define default_layer_debug(...) ((void)0)

typedef uint16_t layer_state_t;
typedef struct { uint8_t col, row; } keypos_t;
typedef enum { TICK_EVENT, KEY_EVENT, ENCODER_CW_EVENT, ENCODER_CCW_EVENT } keyevent_type_t;
typedef struct { keypos_t key; uint16_t time; keyevent_type_t type; bool pressed; } keyevent_t;
typedef struct { bool interrupted : 1; uint8_t count : 4; } tap_t;
typedef struct { keyevent_t event; tap_t tap; } keyrecord_t;
#define KEYLOC_ENCODER_CW 253
#define KEYLOC_ENCODER_CCW 252
#define KEYEQ(a, b) ((a).row == (b).row && (a).col == (b).col)
static inline bool IS_NOEVENT(keyevent_t e) { return e.type == TICK_EVENT; }
static inline bool IS_EVENT(keyevent_t e) { return e.type != TICK_EVENT; }
static inline bool IS_KEYEVENT(keyevent_t e) { return e.type == KEY_EVENT; }
static inline bool IS_ENCODEREVENT(keyevent_t e) { return e.type == ENCODER_CW_EVENT || e.type == ENCODER_CCW_EVENT; }

extern layer_state_t layer_state, default_layer_state;
extern bool disable_action_cache;
extern bool swap_hands, swap_held;
extern const keypos_t hand_swap_config[MATRIX_ROWS][MATRIX_COLS];
extern const uint8_t encoder_hand_swap_config[NUM_ENCODERS];
uint32_t timer_read32(void);
uint16_t timer_read(void);
void clear_weak_mods(void);
void clear_keyboard(void);
void tap_code(uint8_t code);
void tap_code_delay(uint8_t code, uint16_t delay);
void register_code(uint8_t code);
void unregister_code(uint8_t code);
void wait_ms(uint16_t delay);
#define QS_tap_hold_caps_delay 80
#define QS_tap_code_delay 0
void action_exec(keyevent_t event);
void process_hand_swap(keyevent_t *event);
void swap_hands_on(void);
void swap_hands_off(void);
bool is_swap_hands_on(void);
bool pre_process_record_quantum(keyrecord_t *record);
bool process_record_quantum(keyrecord_t *record);
bool process_record_user(uint16_t keycode, keyrecord_t *record);
bool process_record_quantum_helper(uint16_t keycode, keyrecord_t *record);
bool pre_process_record_modules(uint16_t keycode, keyrecord_t *record);
bool pre_process_record_kb(uint16_t keycode, keyrecord_t *record);
void process_record(keyrecord_t *record);
void process_record_handler(keyrecord_t *record);
void process_record_tap_hint(keyrecord_t *record);
void post_process_record_quantum(keyrecord_t *record);
void process_action(keyrecord_t *record, action_t action);
bool is_tap_record(keyrecord_t *record);
bool is_tap_action(action_t action);
uint16_t keymap_key_to_keycode(uint8_t layer, keypos_t key);
uint8_t layer_switch_get_layer(keypos_t key);
action_t action_for_key(uint8_t layer, keypos_t key);
action_t layer_switch_get_action(keypos_t key);
action_t store_or_get_action(bool pressed, keypos_t key);
void update_source_layers_cache(keypos_t key, uint8_t layer);
uint8_t read_source_layers_cache(keypos_t key);
void layer_state_set(layer_state_t state);
bool action_tapping_is_idle(void);
#endif
