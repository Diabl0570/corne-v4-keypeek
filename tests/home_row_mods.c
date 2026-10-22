#include "command_mode_qmk_shim.h"
#include "command_qmk.h"
#include "command_protocol.h"
#include "preset.h"

#ifndef HOME_ROW_TEST_HOME_ROW
#define HOME_ROW_TEST_HOME_ROW 2
#endif

layer_state_t layer_state, default_layer_state = 1;
static uint32_t clock_ms;
static bool keys[256];
static struct { uint8_t mods; bool keys[256]; } reports[4096];
static unsigned report_count;
static unsigned scenarios;
static const uint8_t everyday[] = {0,1,2,6,7,8,9,10,12,13};
static const struct { uint8_t row,col,mods; } home_keys[] = {
    {1,1,8},{1,2,1},{1,3,4},{1,4,8},{5,1,128},{5,2,1},{5,3,64},{5,4,128}
};

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
    cm_home((cm_state_t *)command_mode_state());
    cm_select((cm_state_t *)command_mode_state(),layer);
    command_mode_housekeeping();
    report_count=0;
    ++scenarios;
}

static uint8_t original_tap(uint8_t layer,uint8_t row,uint8_t col) {
    uint16_t code=baseline_maps[layer][row][col];
    if (IS_QK_MOD_TAP(code)) code=QK_MOD_TAP_GET_TAP_KEYCODE(code);
    assert(code<=255);
    return code;
}
static void ordinary_taps_and_holds(void) {
    for (unsigned l=0;l<sizeof(everyday);++l) {
        uint8_t layer=everyday[l];
        for (unsigned h=0;h<sizeof(home_keys)/sizeof(home_keys[0]);++h) {
            uint8_t row=home_keys[h].row,col=home_keys[h].col,mods=home_keys[h].mods;
            select_panel(layer);
            uint8_t tap=original_tap(layer,row,col);
            edge(row,col,true); tick(20); edge(row,col,false); tick(250);
            if (tap!=KC_NO) assert(saw(tap,0));
            for (unsigned i=0;i<report_count;++i) for (unsigned k=0;k<256;++k)
                if (reports[i].keys[k]) assert(k==tap);
            if (tap==KC_NO) {
                action_t decoded=action_for_keycode(preset_maps[layer][row][col]);
                assert(decoded.kind.id==ACT_LMODS || decoded.kind.id==ACT_RMODS);
                assert(!decoded.key.mods && IS_MODIFIER_KEYCODE(decoded.key.code));
                key(1,0); assert(saw(KC_TAB,0));
            }
            released();
            for (unsigned tab=0;tab<2;++tab) {
                select_panel(layer);
                edge(row,col,true); tick(205);
                key(1,tab?6:0);
                assert(saw(KC_TAB,mods));
                edge(row,col,false); released();
            }
        }
    }
    puts("PASS actual preset taps/holds: all eight exact home-row families across ten everyday layers; both Tab positions; neutral taps leave no key or modifier latched");
}
static void command_tab_and_shift(void) {
    for (unsigned l=0;l<sizeof(everyday);++l) for (unsigned side=0;side<2;++side) {
        uint8_t layer=everyday[l],row=side?5:1,mods=side?128:8;
        for (unsigned shift=0;shift<2;++shift) for (unsigned release_first=0;release_first<2;++release_first) {
            select_panel(layer);
            edge(row,1,true); tick(205);
            edge(shift?5:2,shift?6:0,true);
            edge(1,0,true);
            assert(saw(KC_TAB,mods | MOD_BIT(shift?KC_RSFT:KC_LSFT)));
            if (release_first) edge(row,1,false);
            edge(1,0,false);
            edge(shift?5:2,shift?6:0,false);
            if (!release_first) edge(row,1,false);
            released();
        }
        select_panel(layer);
        edge(row,1,true); tick(20); edge(1,0,true); tick(20); edge(1,0,false); tick(180);
        assert(saw(KC_TAB,mods));
        edge(row,1,false); released();
    }
    select_panel(9);
    edge(1,1,true); tick(205); edge(5,1,true); tick(205);
    assert(get_mods()==(8|128));
    edge(1,1,false); assert(get_mods()==128);
    edge(5,1,false); released();
    puts("PASS Command-Tab and Shift-Command-Tab: LGUI/RGUI, left/right Shift, both release orders, short queued Tab and established holds, simultaneous GUI sides");
}
static void fast_rolls_keep_saved_timing(void) {
    for (unsigned l=0;l<sizeof(everyday);++l) {
        uint8_t layer=everyday[l];
        if (layer==1 || layer==2) continue;
        for (unsigned side=0;side<2;++side) for (unsigned order=0;order<2;++order) {
            uint8_t row=side?5:1,mods=side?128:8;
            select_panel(layer);
            edge(row,1,true); tick(20); edge(1,0,true); tick(20);
            if (order) { edge(1,0,false); edge(row,1,false); }
            else { edge(row,1,false); edge(1,0,false); }
            tick(250);
            assert(!saw(KC_TAB,mods));
            assert(saw(KC_TAB,0));
            assert(saw(original_tap(layer,row,1),0));
            released();
        }
    }
    puts("PASS unchanged 200ms timing: early rolls/nested taps remain taps, permissive/hold-on-other stay off");
}
static void put32(uint8_t *p,uint32_t v) { for (unsigned i=0;i<4;++i) p[i]=v>>(i*8); }
static uint8_t request(uint8_t op,uint32_t id,uint32_t sequence,uint8_t layer) {
    uint8_t p[32]={0xD3,0x43,1,op};
    put32(p+4,id); put32(p+8,77); put32(p+12,op==2?0:command_mode_state()->epoch); put32(p+16,sequence); p[20]=layer;
    assert(command_mode_handle_report(p,32));
    return p[8];
}
static void focus_home_and_mirror(void) {
    select_panel(9);
    assert(request(2,1,0,0)==CM_OK);
    cm_auto((cm_state_t *)command_mode_state()); command_mode_housekeeping();
    assert(request(4,2,1,9)==CM_OK);
    edge(1,1,true); tick(205);
    assert(request(4,3,2,8)==CM_DEFERRED);
    assert(command_mode_state()->selection.layer==9);
    key(1,0); assert(saw(KC_TAB,8));
    edge(1,1,false); tick(250); tick(1);
    assert(command_mode_state()->selection.layer==8);
    released();
    for (unsigned established=0;established<2;++established) {
        select_panel(9);
        edge(1,1,true); tick(established?205:20);
        key(HOME_ROW_TEST_HOME_ROW,5);
        assert(command_mode_state()->selection.mode==CM_TYPING);
        tick(220); key(1,0); assert(saw(KC_TAB,8));
        edge(1,1,false); released();
    }
    for (uint8_t layer=7;layer<=9;++layer) {
        select_panel(layer);
        edge(3,5,true); key(7,4); edge(3,5,false); released();
        for (unsigned i=0;i<report_count;++i) {
            if (reports[i].keys[KC_F18] || reports[i].keys[KC_D]) {
                fprintf(stderr,"FAIL panel %u: mirrored physical FN emitted a voice shortcut\n",layer);
                exit(1);
            }
        }
        select_panel(layer);
        edge(3,5,true); assert(is_swap_hands_on());
        edge(5,1,true); tick(205);
        edge(2,0,true); key(5,0); assert(saw(KC_TAB,8|2));
        edge(2,0,false); edge(3,5,false); assert(!is_swap_hands_on());
        edge(5,1,false); released();
        for (unsigned i=0;i<report_count;++i) assert(!reports[i].keys[KC_F18] && !reports[i].keys[KC_D]);
    }
    select_panel(9);
    edge(1,1,true); tick(205); edge(3,5,true);
    edge(5,1,true); edge(1,1,false); edge(5,1,false);
    edge(3,5,false); released();
    select_panel(9);
    edge(3,5,true); edge(5,1,true); tick(205);
    key(HOME_ROW_TEST_HOME_ROW,5); assert(!is_swap_hands_on() && command_mode_state()->selection.mode==CM_TYPING);
    edge(5,1,false); edge(3,5,false); released();
    puts("PASS authority/ownership: focus deferred while GUI held; Home keeps paired releases; Mirror GUI/Tab/Shift/FN avoids voice; collisions and Home clear safely");
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
    ordinary_taps_and_holds();
    command_tab_and_shift();
    fast_rolls_keep_saved_timing();
    focus_home_and_mirror();
    printf("All %u preset/report scenarios passed with UBSan.\n",scenarios);
    return 0;
}
