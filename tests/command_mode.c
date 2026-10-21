#include "command_mode_qmk_shim.h"
#include "command_qmk.h"
#include "command_protocol.h"
#include "command_registry.h"
#include "action_tapping.h"
#include "usb_device_state.h"

_Static_assert(CM_HOME == 0x7E00, "Vial USER00 must resolve to QK_KB_0");
_Static_assert(CM_SPACE_MIRROR == 0x7E03, "Vial USER03 mismatch");
_Static_assert(CM_SELECT_0 == 0x7E04, "Vial USER04 mismatch");
_Static_assert(CM_SELECT_LAST == 0x7E13, "Vial USER19 mismatch");

layer_state_t layer_state, default_layer_state = 1;
static uint32_t clock_ms;
static uint16_t maps[16][8][7], encoders[16][4];
static unsigned held[65536], presses_sent, releases_sent, layer_notifications;
static uint16_t last_press, last_release;
static struct { uint16_t action; bool pressed; uint8_t mods; } output[4096];
static unsigned output_count;

static uint8_t host_mods(void) {
    uint8_t mods = 0;
    for (unsigned i = 0; i < 8; ++i) if (held[ACTION_KEY(KC_LEFT_CTRL + i)]) mods |= 1u << i;
    for (unsigned i = 0; i < 4; ++i) if (held[ACTION_MODS(1u << i)]) mods |= 1u << i;
    return mods;
}

static void emit(uint16_t code, bool pressed) {
    if (pressed) {
        assert(held[code] == 0); ++held[code]; last_press = code; ++presses_sent;
    } else {
        assert(held[code] == 1); --held[code]; last_release = code; ++releases_sent;
    }
    assert(output_count < sizeof(output) / sizeof(output[0]));
    output[output_count].action = code;
    output[output_count].pressed = pressed;
    output[output_count++].mods = host_mods();
}

uint32_t timer_read32(void) { return clock_ms; }
uint16_t timer_read(void) { return clock_ms; }
void clear_weak_mods(void) {}
void clear_keyboard(void) { assert(!"QMK tapping overflow"); }
void process_record_tap_hint(keyrecord_t *record) { (void)record; }
void post_process_record_modules(uint16_t keycode, keyrecord_t *record) { (void)keycode; (void)record; }
void post_process_record_kb(uint16_t keycode, keyrecord_t *record) { post_process_record_user(keycode, record); }
bool pre_process_record_modules(uint16_t keycode, keyrecord_t *record) { (void)keycode; (void)record; return true; }
bool pre_process_record_kb(uint16_t keycode, keyrecord_t *record) { (void)keycode; (void)record; return true; }
bool process_record_quantum_helper(uint16_t keycode, keyrecord_t *record) { return process_record_user(keycode, record); }
void register_code(uint8_t code) { emit(ACTION_KEY(code), true); }
void unregister_code(uint8_t code) { emit(ACTION_KEY(code), false); }
void wait_ms(uint16_t delay) { clock_ms += delay; }
uint16_t keymap_key_to_keycode(uint8_t layer, keypos_t key) {
    assert(layer < 16);
    if (key.row >= 8) return encoders[layer][key.col];
    assert(key.col < 7);
    return maps[layer][key.row][key.col];
}
action_t action_for_key(uint8_t layer, keypos_t key) {
    uint16_t code = keymap_key_to_keycode(layer, key);
    if (IS_QK_MOD_TAP(code)) return (action_t){.code = ACTION_MODS_TAP_KEY((code >> 8) & 0x1F, code & 0xFF)};
    if (code == QK_MOUSE_BUTTON_1) return (action_t){.code = ACTION(ACT_MOUSEKEY, 1)};
    return (action_t){.code = code <= 255 ? ACTION_KEY(code) : ACTION_NO};
}
void process_action(keyrecord_t *record, action_t action) {
    uint16_t code = action.code;
    if (action.kind.id == ACT_LMODS_TAP || action.kind.id == ACT_RMODS_TAP) {
        code = record->tap.count ? ACTION_KEY(action.key.code) : ACTION_MODS(action.key.mods);
    }
    if (!code || code == ACTION_TRANSPARENT) return;
    emit(code, record->event.pressed);
}
void layer_state_set(layer_state_t mask) {
    assert(mask == cm_layer_mask(command_mode_state()));
    assert(is_swap_hands_on() == (command_mode_state()->mirror_holds != 0));
    ++layer_notifications;
    layer_state = mask;
}

static void tick(uint32_t delta) {
    clock_ms += delta;
    action_exec((keyevent_t){.time = timer_read(), .type = TICK_EVENT});
    command_mode_housekeeping();
}
static void edge(uint8_t row, uint8_t col, bool pressed) {
    ++clock_ms;
    action_exec((keyevent_t){.key = {col, row}, .time = timer_read(), .type = KEY_EVENT, .pressed = pressed});
}
static void key(uint8_t row, uint8_t col) { edge(row, col, true); edge(row, col, false); }
static void home(void) { key(0, 0); tick(300); assert(layer_state == 0); }
static void no_held(void) {
    for (unsigned i = 0; i < 65536; ++i) assert(!held[i]);
    assert(presses_sent == releases_sent);
}
static void tap_output(unsigned start, uint16_t keycode) {
    assert(output_count == start + 2);
    assert(output[start].action == ACTION_KEY(keycode) && output[start].pressed && !output[start].mods);
    assert(output[start + 1].action == ACTION_KEY(keycode) && !output[start + 1].pressed && !output[start + 1].mods);
}
static void put32(uint8_t *p, uint32_t value) { for (uint8_t i = 0; i < 4; ++i) p[i] = value >> (8 * i); }
static void request(uint8_t *p, uint8_t opcode, uint32_t id, uint32_t session, uint32_t epoch, uint32_t sequence, uint8_t layer) {
    memset(p, 0, 32);
    p[0] = 0xD3; p[1] = 0x43; p[2] = 1; p[3] = opcode;
    put32(p + 4, id); put32(p + 8, session); put32(p + 12, epoch); put32(p + 16, sequence); p[20] = layer;
}

static void reducer_traces(void) {
    cm_state_t s;
    cm_init(&s);
    cm_menu(&s, true, UINT32_MAX - 50);
    cm_menu(&s, false, 10);
    cm_tick(&s, 209, true); assert(cm_layer_mask(&s) == 0);
    cm_tick(&s, 210, true); assert(cm_layer_mask(&s) == 2);
    cm_control(&s, false, true); assert(cm_layer_mask(&s) == 14);
    cm_control(&s, false, false); assert(cm_layer_mask(&s) == 2);
    cm_home(&s); assert(cm_layer_mask(&s) == 0);
    for (uint8_t layer = 1; layer < 16; ++layer) {
        cm_select(&s, layer); assert(cm_layer_mask(&s) == (uint16_t)(1u << layer));
        cm_control(&s, true, true);
        cm_control(&s, false, true);
        cm_home(&s); assert(s.selection.mode == CM_TYPING && !s.mirror_holds);
        assert(!s.fn_holds && !s.picker && !s.pending && cm_layer_mask(&s) == 0);
    }
    cm_open(&s, 123, 1);
    assert(cm_context(&s, 123, s.epoch, 1, 7, 2, true) == CM_DISARMED);
    cm_auto(&s);
    assert(cm_context(&s, 123, s.epoch, 1, 7, 2, false) == CM_DEFERRED);
    cm_tick(&s, 3, false); assert(s.selection.layer == 6);
    cm_tick(&s, 4, true); assert(s.selection.layer == 7);
    assert(cm_context(&s, 123, s.epoch, 1, 8, 5, true) == CM_STALE_SEQUENCE);
    assert(cm_context(&s, 123, s.epoch, 2, 11, 5, true) == CM_INVALID_LAYER);
    cm_menu(&s, true, 10); cm_tick(&s, 210, true);
    uint32_t picker_epoch = s.epoch;
    assert(s.picker && cm_layer_mask(&s) == 0x8000);
    assert(cm_context(&s, 123, s.epoch, 2, 9, 211, true) == CM_DEFERRED);
    cm_menu(&s, false, 212);
    assert(!s.picker && !s.pending && s.selection.mode == CM_AUTOMATIC && s.selection.layer == 7 && s.epoch != picker_epoch);
    assert(cm_context(&s, 123, picker_epoch, 3, 9, 213, true) == CM_STALE_EPOCH);
    cm_tick(&s, 2211, true); assert(!s.session && s.selection.mode == CM_MANUAL && s.selection.layer == 7);
    cm_open(&s, 456, 2220); assert(s.selection.mode == CM_MANUAL);
    cm_auto(&s); cm_menu(&s, true, 2221); cm_tick(&s, 2421, true);
    cm_close(&s, 456); cm_menu(&s, false, 2422); assert(s.selection.mode == CM_MANUAL);
    cm_configuration(&s, UINT32_MAX - 20); assert(cm_configuration_busy(&s, 100)); assert(!cm_configuration_busy(&s, 1980));
    s.epoch = UINT32_MAX; cm_home(&s); assert(s.epoch == 1 && !s.session);
    s.revision = UINT32_MAX; cm_auto(&s); assert(s.revision == 1 && !s.session && s.selection.mode == CM_MANUAL);
    cm_open(&s, 789, 3000); cm_auto(&s); s.sequence = UINT32_MAX;
    assert(cm_context(&s, 789, s.epoch, 1, 7, 3001, true) == CM_STALE_SEQUENCE && !s.session && s.selection.mode == CM_MANUAL);
    cm_open(&s, 790, 3002); cm_auto(&s); cm_open(&s, 791, 3003); assert(s.selection.mode == CM_MANUAL);
    puts("PASS reducer: wrap-safe single/hold, all 16 Home exits, FN tri-layer, manual/Auto grants, picker epochs, lease and counter wrap");
}

static void protocol_traces(void) {
    cm_state_t s, before;
    cm_protocol_t protocol = {0};
    uint8_t p[32], retry[32], response[32];
    cm_init(&s);
    request(p, 1, 1, 0, 0, 0, 0); before = s;
    assert(cm_report(&protocol, &s, p, 32, 5000, true));
    assert(p[1] == 0xAC && p[8] == CM_OK && p[9] == 16 && p[11] == 2 && p[12] == 0x89 && p[19] == 0x45);
    assert(!memcmp(&before, &s, sizeof(s)));
    request(p, 2, 2, 22, 0, 0, 0); memcpy(retry, p, 32);
    assert(cm_report(&protocol, &s, p, 32, 10, true)); memcpy(response, p, 32);
    uint32_t epoch = s.epoch;
    assert(cm_report(&protocol, &s, retry, 32, 11, true)); assert(!memcmp(response, retry, 32) && s.epoch == epoch);
    cm_auto(&s);
    request(p, 4, 3, 22, s.epoch, 1, 8); memcpy(retry, p, 32);
    cm_report(&protocol, &s, p, 32, 12, false); assert(p[8] == CM_DEFERRED && (p[11] & 4));
    cm_home(&s); cm_report(&protocol, &s, retry, 32, 13, true); assert(retry[8] == CM_STALE_EPOCH && s.selection.mode == CM_TYPING);
    for (unsigned i = 0; i < 32; ++i) {
        request(p, 4, 4, 22, s.epoch, 2, 8);
        if (i >= 21) p[i] = 1;
        else if (i == 2) p[i] = 9;
        else continue;
        before = s; cm_report(&protocol, &s, p, 32, 20, true);
        assert(p[8] != CM_OK && !memcmp(&before, &s, sizeof(s)));
    }
    request(p, 2, 5, 99, 0, 0, 0); before = s; cm_report(&protocol, &s, p, 31, 20, true); assert(!memcmp(&before, &s, sizeof(s)));
    cm_configuration(&s, 30); request(p, 2, 6, 99, 0, 0, 0); cm_report(&protocol, &s, p, 32, 31, true); assert(p[8] == CM_BUSY_CONFIGURATION && !s.session);
    request(p, 2, 7, 99, 0, 0, 0); cm_report(&protocol, &s, p, 32, 2030, true); assert(p[8] == CM_OK && s.selection.mode == CM_TYPING);
    request(p, 4, 8, 99, s.epoch, 1, 15); before = s; cm_report(&protocol, &s, p, 32, 2031, true); assert(p[8] == CM_INVALID_LAYER && !memcmp(&before, &s, sizeof(s)));
    request(p, 3, 9, 98, 0, 0, 0); before = s; cm_report(&protocol, &s, p, 32, 2032, true); assert(p[8] == CM_WRONG_SESSION && !memcmp(&before, &s, sizeof(s)));
    memset(p, 0xC0, 32); before = s; assert(!cm_report(&protocol, &s, p, 32, 2031, true) && !memcmp(&before, &s, sizeof(s)));
    cm_init(&s); protocol = (cm_protocol_t){0};
    request(p, 2, 10, 500, 0, 0, 0); memcpy(retry, p, 32);
    cm_report(&protocol, &s, p, 32, 100, true); cm_report(&protocol, &s, retry, 32, 1900, true);
    assert(retry[8] == CM_OK && s.lease_at == 1900); cm_tick(&s, 2100, true); assert(s.session == 500);
    request(p, 3, 11, 500, 0, 0, 0); memcpy(retry, p, 32);
    cm_report(&protocol, &s, p, 32, 2200, true); cm_report(&protocol, &s, retry, 32, 4000, true);
    assert(retry[8] == CM_OK && s.lease_at == 4000); cm_tick(&s, 4200, true); assert(s.session == 500 && s.selection.mode == CM_TYPING);
    puts("PASS wire: exact capability bytes, idempotent retry, stale ACK invalidation, padding/version/length rejection, configurator quiet period");
}

static void qmk_traces(void) {
    for (unsigned layer = 0; layer < 16; ++layer) {
        maps[layer][0][0] = CM_HOME; maps[layer][0][1] = CM_AUTO;
        maps[layer][0][2] = CM_MIRROR; maps[layer][4][2] = CM_MIRROR;
        maps[layer][0][3] = CM_SELECT_0 + 11; maps[layer][0][4] = CM_SPACE_MIRROR;
        maps[layer][0][5] = CM_SELECT_0 + 1;
        maps[layer][7][4] = QK_TRI_LAYER_UPPER;
        maps[layer][1][0] = KC_A; maps[layer][5][0] = KC_LEFT_SHIFT;
        maps[layer][1][1] = QK_MOD_TAP | (1u << 8) | KC_S;
        maps[layer][5][1] = QK_MOD_TAP | (2u << 8) | KC_F;
        maps[layer][1][2] = QK_MOUSE_BUTTON_1;
        maps[layer][1][6] = KC_Z; maps[layer][5][6] = KC_RIGHT_CTRL;
        for (unsigned encoder = 0; encoder < 4; ++encoder) encoders[layer][encoder] = KC_F1 + encoder;
    }
    maps[1][1][0] = KC_1;
    maps[11][1][0] = KC_B;
    maps[1][1][1] = KC_7; maps[2][1][1] = KC_NO; maps[15][1][1] = KC_NO;
    maps[11][1][1] = QK_MOD_TAP | (4u << 8) | KC_D;
    maps[0][1][3] = KC_F; maps[1][1][3] = KC_4;
    command_mode_housekeeping(); assert(layer_notifications == 0);
    key(3,3); assert(layer_state == 0); tick(199); assert(layer_state == 0); tick(1); assert(layer_state == 2);
    key(7,4); assert(layer_state == 2);
    edge(7,4,true); assert(layer_state == 14); edge(7,4,false); assert(layer_state == 2);
    home();
    edge(3,3,true); edge(1,0,true); assert(layer_state == 2 && last_press == ACTION_KEY(KC_1)); edge(1,0,false); edge(3,3,false); home();
    key(3,3); edge(3,3,true); assert(layer_state == 0 && command_mode_state()->selection.mode == CM_TYPING); edge(3,3,false); tick(300); assert(layer_state == 0);
    edge(3,3,true); tick(200); assert(layer_state == 0x8000); edge(3,3,false); assert(layer_state == 0);
    edge(3,3,true); tick(200); key(0,3); assert(layer_state == (1u << 11)); edge(3,3,false); assert(layer_state == (1u << 11));
    edge(7,4,true); assert(layer_state == (1u << 2)); edge(7,4,false); assert(layer_state == (1u << 11)); home();
    edge(3,3,true); tick(200); key(0,5); edge(3,3,false);
    assert(layer_state == (1u << 1) && command_mode_state()->selection.mode == CM_TYPING);
    edge(7,4,true); assert(layer_state == ((1u << 1) | (1u << 2) | (1u << 3)));
    edge(7,4,false); assert(layer_state == (1u << 1));
    key(3,3); tick(200); assert(layer_state == 0 && command_mode_state()->selection.mode == CM_TYPING);
    unsigned space_start = output_count;
    key(0,4); tap_output(space_start, KC_SPC); assert(!is_swap_hands_on());
    space_start = output_count;
    edge(0,4,true); clock_ms += 200; edge(0,4,false); assert(output_count == space_start && !is_swap_hands_on());
    edge(0,4,true); tick(200); assert(is_swap_hands_on()); key(3,3); edge(3,3,true); assert(!is_swap_hands_on()); edge(3,3,false);
    tick(250); assert(!is_swap_hands_on()); edge(0,4,false); assert(output_count == space_start);
    tick(300);
    edge(0,2,true); assert(is_swap_hands_on()); edge(1,0,true); assert(last_press == ACTION_KEY(KC_LEFT_SHIFT));
    key(3,3); edge(3,3,true); assert(!is_swap_hands_on()); edge(3,3,false);
    unsigned before = presses_sent; edge(5,0,true); assert(presses_sent == before); edge(1,0,false); assert(last_release == ACTION_KEY(KC_LEFT_SHIFT)); edge(5,0,false); edge(0,2,false); no_held(); tick(300);
    edge(0,2,true); edge(1,0,true); edge(0,2,false); before = presses_sent;
    edge(5,0,true); edge(5,0,false); assert(presses_sent == before && held[ACTION_KEY(KC_LEFT_SHIFT)] == 1);
    edge(1,0,false); no_held(); tick(300);
    edge(0,2,true); key(3,3); edge(3,3,true); edge(3,3,false);
    edge(4,2,true); assert(is_swap_hands_on()); edge(0,2,false); assert(is_swap_hands_on()); edge(4,2,false); assert(!is_swap_hands_on()); tick(300);
    edge(7,4,true); key(3,3); edge(3,3,true); edge(3,3,false); assert(layer_state == 0);
    edge(7,4,false); assert(layer_state == 0); tick(300);
    edge(0,2,true); edge(1,6,true); assert(last_press == ACTION_KEY(KC_RIGHT_CTRL)); edge(0,2,false); edge(1,6,false); assert(last_release == ACTION_KEY(KC_RIGHT_CTRL)); no_held();
    for (unsigned row = 0; row < 8; ++row) for (unsigned col = 0; col < 7; ++col) {
        keypos_t partner = hand_swap_config[row][col]; assert(partner.row < 8 && partner.col < 7);
        keypos_t back = hand_swap_config[partner.row][partner.col]; assert(back.row == row && back.col == col);
    }
    for (unsigned enc = 0; enc < 4; ++enc) assert(encoder_hand_swap_config[encoder_hand_swap_config[enc]] == enc);
    edge(0,2,true);
    keyevent_t encoder = {.key = {0, KEYLOC_ENCODER_CW}, .type = ENCODER_CW_EVENT, .pressed = true, .time = timer_read()};
    action_exec(encoder); assert(last_press == ACTION_KEY(KC_F3)); edge(0,2,false); encoder.pressed = false; action_exec(encoder); assert(last_release == ACTION_KEY(KC_F3)); no_held();
    home(); edge(1,2,true); key(0,3); edge(1,2,false); assert(last_release == ACTION(ACT_MOUSEKEY,1)); no_held(); home();
    uint8_t report[32]; request(report, 2, 10, 4242, 0, 0, 0); command_mode_handle_report(report, 32); key(0,1);
    edge(1,1,true); tick(10); edge(1,1,false);
    assert(!action_tapping_is_idle());
    request(report, 4, 11, 4242, command_mode_state()->epoch, 1, 9); command_mode_handle_report(report, 32);
    assert(report[8] == CM_DEFERRED && command_mode_state()->selection.layer == 6);
    tick(300); assert(action_tapping_is_idle() && command_mode_state()->selection.layer == 9); no_held();
    edge(1,1,true); tick(250); assert(held[ACTION_MODS(1)] == 1); home(); edge(1,1,false); tick(300); no_held();
    for (unsigned reverse = 0; reverse < 2; ++reverse) {
        home(); unsigned start = output_count;
        edge(1,1,true); edge(7,4,true);
        if (reverse) { edge(7,4,false); edge(1,1,false); }
        else { edge(1,1,false); edge(7,4,false); }
        tap_output(start, KC_S); no_held(); tick(300);

        home(); start = output_count;
        edge(1,1,true); edge(0,3,true);
        if (reverse) { edge(0,3,false); edge(1,1,false); }
        else { edge(1,1,false); edge(0,3,false); }
        tap_output(start, KC_S); no_held(); tick(300);

        start = output_count; edge(1,1,true); edge(0,0,true);
        if (reverse) { edge(0,0,false); edge(1,1,false); }
        else { edge(1,1,false); edge(0,0,false); }
        tap_output(start, KC_D); no_held(); tick(300);

        home(); start = output_count;
        edge(1,1,true); edge(0,2,true);
        if (reverse) { edge(0,2,false); edge(1,1,false); }
        else { edge(1,1,false); edge(0,2,false); }
        tap_output(start, KC_S); no_held(); tick(300);

        home(); start = output_count;
        edge(1,1,true); edge(3,3,true); edge(1,3,true);
        if (reverse) { edge(1,3,false); edge(1,1,false); }
        else { edge(1,1,false); edge(1,3,false); }
        edge(3,3,false); assert(output_count == start + 4);
        unsigned characters = 0;
        for (unsigned i = start; i < output_count; ++i) {
            assert(!output[i].mods);
            if (output[i].pressed) assert(output[i].action == ACTION_KEY(characters++ ? KC_4 : KC_S));
        }
        assert(characters == 2); no_held(); tick(300);
    }
    home(); unsigned start = output_count;
    edge(1,1,true); edge(7,4,true); tick(250); assert(held[ACTION_MODS(1)] == 1);
    edge(1,1,false); edge(7,4,false); no_held(); assert(output_count == start + 2);
    assert(output[start].action == ACTION_MODS(1) && output[start].mods == 1 && !output[start + 1].mods); tick(300);
    home(); edge(0,2,true); start = output_count; edge(1,1,true);
    key(3,3); edge(3,3,true); edge(3,3,false); edge(1,1,false); edge(0,2,false);
    tap_output(start, KC_F); no_held(); tick(300);
    for (unsigned reverse = 0; reverse < 2; ++reverse) {
        home(); start = output_count;
        edge(1,1,true); edge(0,4,true);
        if (reverse) { edge(0,4,false); edge(1,1,false); }
        else { edge(1,1,false); edge(0,4,false); }
        assert(output_count == start + 4);
        unsigned characters = 0;
        for (unsigned i = start; i < output_count; ++i) {
            assert(!output[i].mods);
            if (output[i].pressed) assert(output[i].action == ACTION_KEY(characters++ ? KC_SPC : KC_S));
        }
        assert(characters == 2); no_held(); tick(300);
    }
    home(); start = output_count;
    edge(1,1,true); tick(180); key(0,4); assert(output_count == start);
    tick(25); assert(held[ACTION_MODS(1)] == 1);
    assert(output_count == start + 3);
    assert(output[start].action == ACTION_MODS(1) && output[start].pressed);
    assert(output[start + 1].action == ACTION_KEY(KC_SPC) && output[start + 1].pressed);
    assert(output[start + 2].action == ACTION_KEY(KC_SPC) && !output[start + 2].pressed);
    for (unsigned i = start; i < output_count; ++i) assert(output[i].mods == 1);
    edge(1,1,false); no_held(); tick(300);

    home(); start = output_count;
    edge(1,1,true); key(0,4); key(0,4); edge(1,1,false);
    assert(output_count == start + 6);
    unsigned characters = 0;
    for (unsigned i = start; i < output_count; ++i) {
        assert(!output[i].mods);
        if (output[i].pressed) assert(output[i].action == ACTION_KEY(characters++ ? KC_SPC : KC_S));
    }
    assert(characters == 3); no_held(); tick(300);

    home(); start = output_count;
    edge(0,4,true); edge(1,1,true); assert(is_swap_hands_on());
    edge(0,4,false); assert(!is_swap_hands_on()); edge(1,1,false);
    tap_output(start, KC_F); no_held(); tick(300);

    home(); start = output_count;
    edge(1,1,true); key(0,4); key(0,0); edge(1,1,false);
    tap_output(start, KC_S); no_held(); tick(300);

    home(); start = output_count;
    edge(0,4,true); key(3,3); edge(3,3,true); edge(3,3,false);
    assert(!is_swap_hands_on()); tick(250); assert(!is_swap_hands_on());
    edge(0,4,false); assert(output_count == start); no_held(); tick(300);

    home(); start = output_count;
    maps[11][0][4] = KC_NO;
    edge(1,1,true); key(0,4); key(0,3); edge(1,1,false);
    assert(output_count == start + 4);
    assert(output[start].action == ACTION_KEY(KC_S) && output[start].pressed);
    assert(output[start + 1].action == ACTION_KEY(KC_SPC) && output[start + 1].pressed);
    for (unsigned i = start; i < output_count; ++i) assert(!output[i].mods);
    no_held(); tick(300); home();
    home(); start = output_count;
    edge(1,1,true); edge(0,2,true); edge(4,4,true);
    edge(0,2,false); edge(4,4,false); edge(1,1,false);
    assert(output_count == start + 4);
    assert(output[start].action == ACTION_KEY(KC_S) && output[start].pressed);
    assert(output[start + 1].action == ACTION_KEY(KC_SPC) && output[start + 1].pressed);
    for (unsigned i = start; i < output_count; ++i) assert(!output[i].mods);
    no_held(); tick(300);

    home(); start = output_count;
    edge(1,1,true); key(0,4); key(0,0); key(0,4); edge(1,1,false);
    assert(output_count == start + 4);
    assert(output[start].action == ACTION_KEY(KC_S) && output[start].pressed);
    assert(output[start + 1].action == ACTION_KEY(KC_SPC) && output[start + 1].pressed);
    for (unsigned i = start; i < output_count; ++i) assert(!output[i].mods);
    no_held(); tick(300);
    home(); key(1,1); start = output_count;
    edge(7,4,true); key(1,1); edge(7,4,false);
    assert(output_count == start);
    key(1,1); tap_output(start, KC_S); no_held(); tick(300);
    home(); start = output_count;
    key(1,1); key(1,1);
    assert(output_count == start + 4);
    for (unsigned i = start; i < output_count; ++i) {
        assert(output[i].action == ACTION_KEY(KC_S) && !output[i].mods);
        assert(output[i].pressed == ((i - start) % 2 == 0));
    }
    no_held(); tick(300);

    home(); start = output_count;
    edge(5,1,true); key(1,1); assert(output_count == start);
    edge(7,4,true); key(1,1); edge(7,4,false);
    key(1,1); edge(5,1,false);
    assert(output_count == start + 6);
    characters = 0;
    for (unsigned i = start; i < output_count; ++i) {
        assert(!output[i].mods);
        if (output[i].pressed) assert(output[i].action == ACTION_KEY(characters++ ? KC_S : KC_F));
    }
    assert(characters == 3); no_held(); tick(300);

    home(); start = output_count;
    edge(5,1,true); key(1,1); key(0,5); key(1,1); edge(5,1,false);
    assert(output_count == start + 4);
    characters = 0;
    for (unsigned i = start; i < output_count; ++i) {
        assert(!output[i].mods);
        if (output[i].pressed) assert(output[i].action == ACTION_KEY(characters++ ? KC_S : KC_F));
    }
    assert(characters == 2); no_held();
    start = output_count; key(1,1); tap_output(start, KC_7); no_held(); home();
    puts("PASS resolved source ownership: completed S then FN uses Symbols, FN release restores S, rapid ss survives, queued repeats retain sources across layer changes");
    puts("PASS queued Space: S then Space in both release orders, pending Ctrl hold reports, repeated taps, interrupted Mirror, held/queued Home cancellation and source-layer change");
    puts("PASS replay source ownership: unresolved home-row taps survive FN, manual, Home, mirror and interrupted Menu in both release orders; holds retain original modifier");
    for (unsigned reason = 0; reason < 3; ++reason) {
        usb_device_state_set_configuration(true, 1);
        uint32_t session = 9000 + reason;
        request(report, 2, 20, session, 0, 0, 0); command_mode_handle_report(report, 32); key(0,1);
        request(report, 4, 21, session, command_mode_state()->epoch, 1, 7); command_mode_handle_report(report, 32);
        usb_device_state_set_leds(1); assert(command_mode_state()->selection.mode == CM_AUTOMATIC);
        edge(0,2,true); edge(1,0,true); assert(held[ACTION_KEY(KC_LEFT_SHIFT)] == 1);
        request(report, 4, 22, session, command_mode_state()->epoch, 2, 9); command_mode_handle_report(report, 32); assert(report[8] == CM_DEFERRED);
        uint32_t epoch = command_mode_state()->epoch;
        if (reason == 0) usb_device_state_set_suspend(true, 1);
        else if (reason == 1) usb_device_state_set_configuration(false, 0);
        else usb_device_state_set_reset();
        const cm_state_t *s = command_mode_state();
        assert(s->selection.mode == CM_MANUAL && s->selection.layer == 7 && !s->session && !s->pending && s->epoch != epoch);
        assert(is_swap_hands_on() && held[ACTION_KEY(KC_LEFT_SHIFT)] == 1);
        if (reason == 0) usb_device_state_set_resume(true, 1);
        else usb_device_state_set_configuration(true, 1);
        request(report, 3, 23, session, 0, 0, 0); command_mode_handle_report(report, 32);
        assert(report[8] == CM_WRONG_SESSION && command_mode_state()->selection.mode == CM_MANUAL);
        edge(1,0,false); edge(0,2,false); assert(last_release == ACTION_KEY(KC_LEFT_SHIFT)); no_held(); home();
    }
    puts("PASS pinned USB lifecycle: suspend/unconfigure/reset revoke authority with paused clock, late wake STATE fails, mirrored held releases remain paired");
    puts("PASS pinned QMK: interrupted lookup, double/hold/picker, FN, generation-owned controls, full swap/encoder involution, collisions, modifiers/mouse releases, actual tapping-idle deferral");
}

int main(void) {
    reducer_traces(); protocol_traces(); qmk_traces();
    puts("All command-mode tests passed with UBSan.");
}
