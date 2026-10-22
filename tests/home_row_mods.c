#include "command_mode_qmk_shim.h"
#include "command_qmk.h"
#include "command_protocol.h"
#include "preset.h"

layer_state_t layer_state, default_layer_state = 1;
static uint32_t clock_ms;
static bool keys[256];
static struct { uint8_t mods; bool keys[256]; } reports[4096];
static unsigned report_count;

uint32_t timer_read32(void) { return clock_ms; }
uint16_t timer_read(void) { return clock_ms; }
void wait_ms(uint16_t delay) { clock_ms += delay; }
void clear_keyboard(void) { assert(!"QMK tapping buffer overflow"); }
void process_record_tap_hint(keyrecord_t *record) {}
void post_process_record_modules(uint16_t keycode, keyrecord_t *record) {}
void post_process_record_kb(uint16_t keycode, keyrecord_t *record) { post_process_record_user(keycode, record); }
bool pre_process_record_modules(uint16_t keycode, keyrecord_t *record) { return true; }
bool pre_process_record_kb(uint16_t keycode, keyrecord_t *record) { return true; }
bool process_record_quantum_helper(uint16_t keycode, keyrecord_t *record) { return process_record_user(keycode,record); }
uint16_t keymap_key_to_keycode(uint8_t layer, keypos_t key) { return key.row < 8 ? preset_maps[layer][key.row][key.col] : KC_NO; }
void layer_state_set(layer_state_t value) { layer_state = value; }
void add_key(uint8_t code) { assert(!keys[code]); keys[code] = true; }
void del_key(uint8_t code) { keys[code] = false; }
bool is_key_pressed(uint8_t code) { return keys[code]; }
void send_keyboard_report(void) {
    assert(report_count < sizeof(reports)/sizeof(reports[0]));
    reports[report_count].mods = get_mods() | get_weak_mods();
    memcpy(reports[report_count++].keys,keys,sizeof(keys));
}
static void tick(uint32_t delta) {
    clock_ms += delta;
    action_exec((keyevent_t){.type=TICK_EVENT,.time=timer_read()});
    command_mode_housekeeping();
}
static void edge(uint8_t row, uint8_t col, bool pressed) {
    ++clock_ms;
    action_exec((keyevent_t){.key={col,row},.type=KEY_EVENT,.time=timer_read(),.pressed=pressed});
}
static void key(uint8_t row,uint8_t col) { edge(row,col,true); edge(row,col,false); }
static bool saw(uint8_t code,uint8_t mods) {
    for (unsigned i=0;i<report_count;++i) if (reports[i].keys[code] && reports[i].mods==mods) return true;
    return false;
}
static void released(void) {
    assert(!get_mods() && !get_weak_mods());
    for (unsigned i=0;i<256;++i) assert(!keys[i]);
    tick(250);
    assert(action_tapping_is_idle());
}
static void select_panel(uint8_t layer) {
    released();
    command_mode_housekeeping();
    cm_init((cm_state_t *)command_mode_state());
    cm_select((cm_state_t *)command_mode_state(),layer);
    command_mode_housekeeping();
    report_count=0;
}
int main(void) {
    select_panel(9);
    edge(1,1,true); tick(220); key(1,0); edge(1,1,false); tick(250);
    if (!saw(KC_TAB,MOD_BIT(KC_LGUI))) {
        fprintf(stderr,"FAIL Browser: held A-position + familiar Tab emitted no LGUI+Tab report\n");
        return 1;
    }
    released();
    puts("PASS Browser: held A-position + familiar Tab emitted LGUI+Tab");
    return 0;
}
