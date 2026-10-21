#include "command_state.h"
#include "command_registry.h"

#include <limits.h>
#include <string.h>

static void changed(cm_state_t *s) {
    if (s->revision == UINT32_MAX) {
        s->session = 0;
        s->pending = false;
        if (s->selection.mode == CM_AUTOMATIC) s->selection.mode = CM_MANUAL;
        if (s->picker_parent.mode == CM_AUTOMATIC) s->picker_parent.mode = CM_MANUAL;
        s->revision = 0;
    }
    ++s->revision;
}

static void boundary(cm_state_t *s) {
    if (s->epoch == UINT32_MAX) {
        s->session = 0;
        if (s->selection.mode == CM_AUTOMATIC) s->selection.mode = CM_MANUAL;
        if (s->picker_parent.mode == CM_AUTOMATIC) s->picker_parent.mode = CM_MANUAL;
        s->epoch = 0;
    }
    ++s->epoch;
    s->pending = false;
    changed(s);
}

static void disarm(cm_state_t *s) {
    if (s->selection.mode == CM_AUTOMATIC) s->selection.mode = CM_MANUAL;
    if (s->picker_parent.mode == CM_AUTOMATIC) s->picker_parent.mode = CM_MANUAL;
    s->pending = false;
}

void cm_init(cm_state_t *s) {
    memset(s, 0, sizeof(*s));
    s->epoch = s->revision = 1;
}

uint16_t cm_layer_mask(const cm_state_t *s) {
    if (s->picker) return (uint16_t)1u << CM_PICKER_LAYER;
    if (s->fn_holds) {
        return (uint16_t)1u << 2 | ((s->selection.mode == CM_TYPING && s->selection.numbers) ? ((1u << 1) | (1u << 3)) : 0);
    }
    if (s->selection.mode == CM_TYPING) return s->selection.numbers ? (1u << 1) : 0;
    return (uint16_t)1u << s->selection.layer;
}

void cm_home(cm_state_t *s) {
    s->selection = (cm_selection_t){CM_TYPING, 0, false};
    s->picker_parent = s->selection;
    s->picker = false;
    s->menu = CM_MENU_CONSUMED;
    s->fn_holds = s->mirror_holds = 0;
    ++s->home_generation;
    boundary(s);
}

void cm_select(cm_state_t *s, uint8_t layer) {
    if (layer == 0) {
        cm_home(s);
        return;
    }
    s->selection = (cm_selection_t){CM_MANUAL, layer, false};
    s->picker = false;
    s->menu = CM_MENU_CONSUMED;
    boundary(s);
}

void cm_auto(cm_state_t *s) {
    uint8_t layer = cm_auto_layer_valid(s->selection.layer) ? s->selection.layer : CM_GENERIC_LAYER;
    s->selection = (cm_selection_t){CM_AUTOMATIC, layer, false};
    s->picker = false;
    s->menu = CM_MENU_CONSUMED;
    boundary(s);
}

static void single(cm_state_t *s) {
    bool numbers = s->selection.mode == CM_TYPING ? !s->selection.numbers : true;
    s->selection = (cm_selection_t){CM_TYPING, 0, numbers};
    s->picker = false;
    boundary(s);
}

static void open_picker(cm_state_t *s) {
    s->picker_parent = s->selection;
    s->picker = true;
    s->menu = CM_MENU_PICKER;
    boundary(s);
}

void cm_menu(cm_state_t *s, bool pressed, uint32_t now) {
    if (pressed) {
        if (s->menu == CM_MENU_GAP && (uint32_t)(now - s->gesture_at) < CM_GESTURE_MS) {
            cm_home(s);
        } else {
            if (s->menu == CM_MENU_GAP) single(s);
            s->menu = CM_MENU_DOWN;
            s->gesture_at = now;
        }
        return;
    }
    if (s->menu == CM_MENU_DOWN && (uint32_t)(now - s->gesture_at) >= CM_GESTURE_MS) open_picker(s);
    if (s->menu == CM_MENU_PICKER) {
        s->selection = s->picker_parent;
        s->picker = false;
        boundary(s);
        s->menu = CM_MENU_IDLE;
    } else if (s->menu == CM_MENU_DOWN) {
        s->menu = CM_MENU_GAP;
        s->gesture_at = now;
    } else {
        s->menu = CM_MENU_IDLE;
    }
}

void cm_interrupt(cm_state_t *s, uint32_t now) {
    if (s->menu == CM_MENU_DOWN) {
        if ((uint32_t)(now - s->gesture_at) >= CM_GESTURE_MS) open_picker(s);
        else {
            single(s);
            s->menu = CM_MENU_CONSUMED;
        }
    } else if (s->menu == CM_MENU_GAP) {
        single(s);
        s->menu = CM_MENU_IDLE;
    }
}

void cm_control(cm_state_t *s, bool mirror, bool pressed) {
    uint8_t *count = mirror ? &s->mirror_holds : &s->fn_holds;
    if (pressed) ++*count;
    else if (*count) --*count;
    changed(s);
}

void cm_tick(cm_state_t *s, uint32_t now, bool quiescent) {
    if (s->session && (uint32_t)(now - s->lease_at) >= CM_LEASE_MS) {
        s->session = 0;
        disarm(s);
        boundary(s);
    }
    if (s->menu == CM_MENU_DOWN && (uint32_t)(now - s->gesture_at) >= CM_GESTURE_MS) open_picker(s);
    if (s->menu == CM_MENU_GAP && (uint32_t)(now - s->gesture_at) >= CM_GESTURE_MS) {
        single(s);
        s->menu = CM_MENU_IDLE;
    }
    if (s->pending && !s->picker && s->selection.mode == CM_AUTOMATIC && quiescent) {
        s->selection.layer = s->pending_layer;
        s->pending = false;
        changed(s);
    }
}

void cm_configuration(cm_state_t *s, uint32_t now) {
    s->configuration_seen = true;
    s->configuration_at = now;
    s->session = 0;
    disarm(s);
    boundary(s);
}

bool cm_configuration_busy(const cm_state_t *s, uint32_t now) {
    return s->configuration_seen && (uint32_t)(now - s->configuration_at) < CM_LEASE_MS;
}

cm_status_t cm_open(cm_state_t *s, uint32_t session, uint32_t now) {
    if (s->session != session) {
        disarm(s);
        s->session = session;
        s->sequence = 0;
        boundary(s);
    }
    s->lease_at = now;
    return CM_OK;
}

cm_status_t cm_renew(cm_state_t *s, uint32_t session, uint32_t now) {
    if (!session || session != s->session) return CM_WRONG_SESSION;
    s->lease_at = now;
    return CM_OK;
}

cm_status_t cm_context(cm_state_t *s, uint32_t session, uint32_t epoch,
                       uint32_t sequence, uint8_t layer, uint32_t now, bool quiescent) {
    if (!session || session != s->session) return CM_WRONG_SESSION;
    if (epoch != s->epoch) return CM_STALE_EPOCH;
    if (!cm_auto_layer_valid(layer)) return CM_INVALID_LAYER;
    if (!sequence || sequence <= s->sequence) {
        if (s->sequence == UINT32_MAX) {
            s->session = 0;
            disarm(s);
            boundary(s);
        }
        return CM_STALE_SEQUENCE;
    }
    if (s->selection.mode != CM_AUTOMATIC) return CM_DISARMED;
    s->sequence = sequence;
    s->lease_at = now;
    if (s->picker || !quiescent) {
        s->pending = true;
        s->pending_layer = layer;
        changed(s);
        return CM_DEFERRED;
    }
    s->selection.layer = layer;
    s->pending = false;
    changed(s);
    return CM_OK;
}

cm_status_t cm_close(cm_state_t *s, uint32_t session) {
    if (!session || session != s->session) return CM_WRONG_SESSION;
    s->session = 0;
    disarm(s);
    boundary(s);
    return CM_OK;
}
