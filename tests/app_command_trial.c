#define HOME_ROW_TEST_HOME_ROW 0
#define main source_regression_main
#include "home_row_mods.c"
#undef main

#include <stdarg.h>

static const uint8_t app_layers[] = {6,7,8,9,10,13};
static struct { uint8_t layer,row,col; bool mirror,automatic; } trial;
static uint32_t trial_session = 1000, trial_request_id = 1000;

static void require_trial(bool condition, const char *format, ...) {
    if (condition) return;
    fprintf(stderr,"FAIL layer %u %s Mirror=%u physical [%u,%u]: ",
            trial.layer,trial.automatic?"Auto":"manual",trial.mirror,trial.row,trial.col);
    va_list args;
    va_start(args,format);
    vfprintf(stderr,format,args);
    va_end(args);
    fputc('\n',stderr);
    exit(1);
}

static uint8_t physical_row(uint8_t logical_row) {
    return trial.mirror ? (logical_row < 4 ? logical_row + 4 : logical_row - 4) : logical_row;
}

static uint8_t trial_request(uint8_t op, uint32_t sequence, uint8_t layer) {
    uint8_t packet[32] = {0xD3,0x43,1,op};
    put32(packet+4,++trial_request_id);
    put32(packet+8,trial_session);
    if (op == 4) {
        put32(packet+12,command_mode_state()->epoch);
        put32(packet+16,sequence);
        packet[20] = layer;
    }
    require_trial(command_mode_handle_report(packet,sizeof(packet)),"protocol request was not handled");
    return packet[8];
}

static void begin_trial(uint8_t layer, bool mirror, bool automatic) {
    trial.layer = layer;
    trial.mirror = mirror;
    trial.automatic = automatic;
    trial.row = trial.col = 0;
    select_panel(layer);
    if (automatic) {
        ++trial_session;
        require_trial(trial_request(2,0,0) == CM_OK,"OPEN failed");
        cm_auto((cm_state_t *)command_mode_state());
        command_mode_housekeeping();
        require_trial(trial_request(4,1,layer) == CM_OK,"Auto context selection failed");
    }
    require_trial(command_mode_state()->selection.layer == layer,"wrong selected layer");
    require_trial(command_mode_state()->selection.mode == (automatic?CM_AUTOMATIC:CM_MANUAL),"wrong selection mode");
    if (mirror) edge(3,5,true);
    require_trial(is_swap_hands_on() == mirror,"Mirror did not match held physical [3,5]");
    report_count = 0;
}

static void finish_trial(void) {
    if (trial.mirror) edge(3,5,false);
    released();
    require_trial(!is_swap_hands_on(),"Mirror remained active after release");
    require_trial(!command_mode_state()->fn_holds && !command_mode_state()->mirror_holds,"control remained held");
}

static void require_shortcut(uint8_t code, uint8_t mods) {
    unsigned downs = 0, ups = 0;
    bool down = false;
    for (unsigned i = 0; i < report_count; ++i) {
        for (unsigned k = 0; k < 256; ++k)
            require_trial(!reports[i].keys[k] || k == code,"report %u emitted unexpected keycode %u, expected %u",i,k,code);
        require_trial(reports[i].mods == 0 || reports[i].mods == mods,
                      "report %u modifier mask %u, expected 0 or %u",i,reports[i].mods,mods);
        bool pressed = reports[i].keys[code];
        if (pressed) require_trial(reports[i].mods == mods,"keycode %u report %u mask %u, expected %u",code,i,reports[i].mods,mods);
        if (pressed && !down) ++downs;
        if (!pressed && down) ++ups;
        down = pressed;
    }
    require_trial(downs == 1 && ups == 1 && !down,"keycode %u had %u downs and %u ups, expected one paired press",code,downs,ups);
    require_trial(!get_mods() && !get_weak_mods(),"shortcut left a modifier held");
}

static void require_modifiers_only(uint8_t mods) {
    for (unsigned i = 0; i < report_count; ++i) {
        require_trial(reports[i].mods == 0 || reports[i].mods == mods,
                      "report %u modifier mask %u, expected 0 or %u",i,reports[i].mods,mods);
        for (unsigned k = 0; k < 256; ++k)
            require_trial(!reports[i].keys[k],"report %u emitted unexpected keycode %u",i,k);
    }
}

static void shortcut_at(uint8_t layer, bool mirror, bool automatic, uint8_t row, uint8_t col, uint8_t code, uint8_t mods) {
    begin_trial(layer,mirror,automatic);
    trial.row = physical_row(row);
    trial.col = col;
    edge(trial.row,col,true);
    tick(20);
    edge(trial.row,col,false);
    finish_trial();
    require_shortcut(code,mods);
}

static void lower_row_commands(void) {
    static const uint8_t edit_codes[] = {KC_Z,KC_X,KC_C,KC_V,KC_F};
    for (unsigned l = 0; l < sizeof(app_layers); ++l)
        for (unsigned automatic = 0; automatic <= (app_layers[l] <= 10); ++automatic)
            for (unsigned mirror = 0; mirror < 2; ++mirror)
                for (unsigned side = 0; side < 2; ++side)
                    for (unsigned col = 1; col <= 5; ++col)
                        shortcut_at(app_layers[l],mirror,automatic,side?6:2,col,edit_codes[col-1],MOD_BIT(KC_LGUI));
    puts("PASS trial edit/Find reports: all six layers, both lower rows, both Mirror states, manual and eligible Auto contexts; exact LGUI mask and paired releases");
}

static void assistant_shortcuts(void) {
    for (unsigned automatic = 0; automatic < 2; ++automatic)
        for (unsigned mirror = 0; mirror < 2; ++mirror) {
            for (unsigned side = 0; side < 2; ++side) {
                shortcut_at(7,mirror,automatic,side?4:0,1,KC_LEFT,12);
                shortcut_at(7,mirror,automatic,side?4:0,2,KC_RIGHT,12);
            }
            shortcut_at(7,mirror,automatic,0,6,KC_SPACE,12);
            begin_trial(7,mirror,automatic);
            trial.row = physical_row(4);
            trial.col = 6;
            edge(trial.row,6,true); tick(220); edge(trial.row,6,false);
            finish_trial();
            require_modifiers_only(0);
            shortcut_at(8,mirror,automatic,0,6,KC_D,7);
        }
    puts("PASS assistant reports: Q/P previous and W/O next use exact Option-Command arrows; OpenAI dictation uses Option-Command-Space, opposite auxiliary stays neutral, Claude stays Control-Option-Shift-D");
}

static void home_with_gui(uint8_t layer, bool mirror, bool automatic, unsigned side, bool established, bool menu) {
    begin_trial(layer,mirror,automatic);
    uint8_t gui_row = physical_row(1);
    edge(gui_row,1,true);
    tick(established?205:20);
    if (automatic) {
        require_trial(trial_request(4,2,layer == 6 ? 7 : 6) == CM_DEFERRED,"held GUI did not defer context");
        require_trial(command_mode_state()->pending,"deferred context was not pending");
    }
    uint32_t epoch = command_mode_state()->epoch;
    if (menu) {
        trial.row = 3; trial.col = 3;
        key(3,3); tick(20); key(3,3);
    } else {
        trial.row = physical_row((layer == 12 ? 2 : 0) + side*4);
        trial.col = 5;
        key(trial.row,5);
    }
    const cm_state_t *state = command_mode_state();
    require_trial(state->selection.mode == CM_TYPING && state->selection.layer == 0 && !state->selection.numbers,
                  "Home did not select Typing layer 0");
    require_trial(state->epoch != epoch,"Home did not change epoch");
    require_trial(!state->pending,"Home retained deferred Auto context");
    require_trial(!is_swap_hands_on() && !state->mirror_holds && !state->fn_holds,"Home did not clear Mirror/FN");
    uint8_t owned_layer = 255;
    require_trial(command_mode_source_layer((keypos_t){1,1},&owned_layer) && owned_layer == layer,
                  "Home lost the held GUI source layer, got %u",owned_layer);
    if (automatic) require_trial(trial_request(4,3,layer) == CM_DISARMED,"Home did not disarm Auto context");
    tick(220);
    require_trial(get_mods() == MOD_BIT(KC_LGUI),"held GUI after Home has mask %u, expected 8",get_mods());
    key(1,0);
    edge(gui_row,1,false);
    finish_trial();
    require_shortcut(KC_TAB,MOD_BIT(KC_LGUI));
    require_trial(command_mode_state()->selection.mode == CM_TYPING && !command_mode_state()->pending,
                  "released keys restored Auto or deferred context after Home");
    require_trial(!command_mode_source_layer((keypos_t){1,1},&owned_layer),"released GUI retained source ownership");
}

static void home_and_menu_recovery(void) {
    for (unsigned l = 0; l < sizeof(app_layers); ++l)
        for (unsigned automatic = 0; automatic <= (app_layers[l] <= 10); ++automatic)
            for (unsigned mirror = 0; mirror < 2; ++mirror)
                for (unsigned established = 0; established < 2; ++established) {
                    for (unsigned side = 0; side < 2; ++side)
                        home_with_gui(app_layers[l],mirror,automatic,side,established,false);
                    home_with_gui(app_layers[l],mirror,automatic,0,established,true);
                }
    for (unsigned mirror = 0; mirror < 2; ++mirror)
        for (unsigned side = 0; side < 2; ++side)
            home_with_gui(12,mirror,false,side,true,false);
    puts("PASS Home/Menu recovery: T/Y across six layers, absolute physical Menu double tap, Review B/N unchanged; pending and established GUI retains source-owned release; Home advances epoch, clears Mirror/pending Auto and emits no Find");
}

static void require_no_voice(void) {
    for (unsigned i = 0; i < report_count; ++i) {
        require_trial(!reports[i].keys[KC_F18],"guard emitted F18 in report %u",i);
        require_trial(!(reports[i].keys[KC_SPACE] && (reports[i].mods & 12) == 12),"guard emitted Option-Command-Space in report %u",i);
        require_trial(!(reports[i].keys[KC_D] && (reports[i].mods & 7) == 7),"guard emitted Control-Option-Shift-D in report %u",i);
    }
}

static void shift_and_fn_guards(void) {
    static const uint8_t layers[] = {6,7,8,9,10,12,13};
    static const struct { uint8_t row,col; } guards[] = {{2,0},{5,6},{6,0},{7,4},{3,4}};
    for (unsigned l = 0; l < sizeof(layers); ++l)
        for (unsigned automatic = 0; automatic <= (layers[l] <= 10); ++automatic)
            for (unsigned mirror = 0; mirror < 2; ++mirror)
                for (unsigned logical = 0; logical <= mirror; ++logical)
                    for (unsigned g = 0; g < sizeof(guards)/sizeof(guards[0]); ++g) {
                        begin_trial(layers[l],mirror,automatic);
                        trial.row = logical ? physical_row(guards[g].row) : guards[g].row;
                        trial.col = guards[g].col;
                        uint8_t logical_row = physical_row(trial.row);
                        uint8_t mods = trial.col == 0 ? MOD_BIT(KC_LSFT) :
                                       trial.col == 6 && logical_row == 5 ? MOD_BIT(KC_RSFT) : 0;
                        bool fn = trial.col == 4 && logical_row == 7;
                        bool tab = trial.col == 6 && logical_row == 1;
                        edge(trial.row,trial.col,true); tick(220);
                        require_trial(get_mods() == mods && !get_weak_mods(),"held guard mask %u, expected %u",get_mods()|get_weak_mods(),mods);
                        require_trial(command_mode_state()->fn_holds == fn,"held FN count %u, expected %u",command_mode_state()->fn_holds,fn);
                        edge(trial.row,trial.col,false);
                        finish_trial();
                        require_no_voice();
                        if (tab) require_shortcut(KC_TAB,0);
                        else require_modifiers_only(mods);
                    }
    puts("PASS held Shift/FN guards: physical and mirrored logical Shift positions, FN [7,4], counterpart [3,4], all six layers plus Review, both Mirror states; no F18 or either assistant voice chord");
}

static void picker_import_selectors(void) {
    for (unsigned mirror = 0; mirror < 2; ++mirror)
        for (unsigned side = 0; side < 2; ++side)
            for (unsigned col = 0; col < 4; ++col) {
                begin_trial(9,mirror,false);
                edge(3,3,true); tick(205);
                require_trial(command_mode_state()->picker && layer_state == (1u << 15),"held physical Menu did not open Picker layer 15");
                require_trial(is_swap_hands_on() == mirror,"opening Picker changed held Mirror");
                uint8_t row = side?6:2, selected = 12 + col;
                trial.row = physical_row(row);
                trial.col = col;
                key(trial.row,col);
                const cm_state_t *state = command_mode_state();
                require_trial(!state->picker && state->selection.mode == CM_MANUAL && state->selection.layer == selected,
                              "Picker logical [%u,%u] selected mode %u layer %u, expected manual layer %u with Picker closed",
                              row,col,state->selection.mode,state->selection.layer,selected);
                edge(3,3,false);
                require_trial(!state->picker && state->selection.mode == CM_MANUAL && state->selection.layer == selected,
                              "Menu release lost selected layer %u",selected);
                finish_trial();
                require_trial(!state->picker && state->selection.mode == CM_MANUAL && state->selection.layer == selected && layer_state == (1u << selected),
                              "Mirror release lost manual layer %u",selected);
                require_no_voice();
                require_modifiers_only(0);
            }
    puts("PASS Picker selector reports: all eight layer 12..15 cells in both Mirror states; held physical Menu opens Picker, selection survives Menu/Mirror release, no host keys or modifiers");
}

int main(void) {
    if (source_regression_main()) return 1;
    require_trial(scenarios == 385,"source regression count changed to %u",scenarios);
    lower_row_commands();
    assistant_shortcuts();
    home_and_menu_recovery();
    shift_and_fn_guards();
    picker_import_selectors();
    printf("All %u preset/report scenarios passed with UBSan: 385 original regressions plus %u app-command trial scenarios.\n",scenarios,scenarios-385);
    return 0;
}
