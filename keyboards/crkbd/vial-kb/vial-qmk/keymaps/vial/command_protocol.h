#pragma once

#include "command_state.h"

#define CM_REPORT_SIZE 32u

typedef struct {
    uint8_t request[CM_REPORT_SIZE], response[CM_REPORT_SIZE];
    uint32_t revision;
    bool cached;
} cm_protocol_t;

bool cm_report(cm_protocol_t *protocol, cm_state_t *state, uint8_t *data,
               uint8_t length, uint32_t now, bool quiescent);
