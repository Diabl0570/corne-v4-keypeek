#ifndef HOME_ROW_MODS_SHIM_H
#define HOME_ROW_MODS_SHIM_H
#include "quantum_keycodes.h"
#include "keycode.h"
action_t action_for_keycode(uint16_t keycode);
static inline uint16_t keycode_config(uint16_t code) { return code; }
static inline uint8_t mod_config(uint8_t mods) { return mods; }
uint8_t get_mods(void);
uint8_t get_weak_mods(void);
void add_mods(uint8_t mods);
void del_mods(uint8_t mods);
void set_mods(uint8_t mods);
void clear_mods(void);
void add_weak_mods(uint8_t mods);
void del_weak_mods(uint8_t mods);
void register_mods(uint8_t mods);
void unregister_mods(uint8_t mods);
void send_keyboard_report(void);
void add_key(uint8_t code);
void del_key(uint8_t code);
bool is_key_pressed(uint8_t code);
static inline bool command_proc(uint8_t code) { return false; }
static inline void register_mouse(uint8_t code, bool pressed) { assert(!"unexpected mouse action"); }
#define QS_tapping_toggle 5
#define qs_wait_ms wait_ms
#define UNEXPECTED_LAYER_STUB(name) static inline void name(layer_state_t value) { assert(!"unexpected native layer action"); }
UNEXPECTED_LAYER_STUB(default_layer_and)
UNEXPECTED_LAYER_STUB(default_layer_or)
UNEXPECTED_LAYER_STUB(default_layer_xor)
UNEXPECTED_LAYER_STUB(default_layer_set)
UNEXPECTED_LAYER_STUB(layer_and)
UNEXPECTED_LAYER_STUB(layer_or)
UNEXPECTED_LAYER_STUB(layer_xor)
UNEXPECTED_LAYER_STUB(layer_on)
UNEXPECTED_LAYER_STUB(layer_off)
UNEXPECTED_LAYER_STUB(layer_invert)
UNEXPECTED_LAYER_STUB(layer_move)
static inline void layer_clear(void) { assert(!"unexpected native layer action"); }
static inline uint8_t host_keyboard_leds(void) { return 0; }
static inline void led_set(uint8_t value) {}
#endif
