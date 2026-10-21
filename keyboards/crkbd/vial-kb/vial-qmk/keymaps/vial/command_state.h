#pragma once

#include <stdbool.h>
#include <stdint.h>

#define CM_GESTURE_MS 200u
#define CM_LEASE_MS 2000u

typedef enum { CM_TYPING, CM_MANUAL, CM_AUTOMATIC } cm_mode_t;
typedef enum { CM_MENU_IDLE, CM_MENU_DOWN, CM_MENU_GAP, CM_MENU_PICKER, CM_MENU_CONSUMED } cm_menu_t;
typedef enum {
    CM_OK, CM_DEFERRED, CM_DISARMED, CM_STALE_EPOCH, CM_STALE_SEQUENCE,
    CM_INVALID_LAYER, CM_BAD_REQUEST, CM_WRONG_SESSION, CM_BUSY_CONFIGURATION,
    CM_UNSUPPORTED_VERSION
} cm_status_t;

typedef struct {
    cm_mode_t mode;
    uint8_t layer;
    bool numbers;
} cm_selection_t;

typedef struct {
    cm_selection_t selection, picker_parent;
    cm_menu_t menu;
    bool picker, pending, configuration_seen;
    uint8_t pending_layer, fn_holds, mirror_holds;
    uint32_t epoch, revision, home_generation;
    uint32_t session, sequence, lease_at, gesture_at, configuration_at;
} cm_state_t;

void cm_init(cm_state_t *state);
uint16_t cm_layer_mask(const cm_state_t *state);
void cm_home(cm_state_t *state);
void cm_select(cm_state_t *state, uint8_t layer);
void cm_auto(cm_state_t *state);
void cm_menu(cm_state_t *state, bool pressed, uint32_t now);
void cm_interrupt(cm_state_t *state, uint32_t now);
void cm_control(cm_state_t *state, bool mirror, bool pressed);
void cm_tick(cm_state_t *state, uint32_t now, bool quiescent);
void cm_configuration(cm_state_t *state, uint32_t now);
void cm_session_lost(cm_state_t *state);
bool cm_configuration_busy(const cm_state_t *state, uint32_t now);
cm_status_t cm_open(cm_state_t *state, uint32_t session, uint32_t now);
cm_status_t cm_renew(cm_state_t *state, uint32_t session, uint32_t now);
cm_status_t cm_context(cm_state_t *state, uint32_t session, uint32_t epoch,
                       uint32_t sequence, uint8_t layer, uint32_t now, bool quiescent);
cm_status_t cm_close(cm_state_t *state, uint32_t session);
