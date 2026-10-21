#include "command_protocol.h"
#include "command_registry.h"

#include <string.h>

enum { CM_CAPABILITIES = 1, CM_OPEN, CM_STATE, CM_CONTEXT, CM_CLOSE };

static uint32_t read32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static void write32(uint8_t *p, uint32_t value) {
    for (uint8_t i = 0; i < 4; ++i) p[i] = value >> (8 * i);
}

static void reply(uint8_t *data, uint8_t opcode, uint32_t request_id, cm_status_t status, const cm_state_t *s) {
    memset(data, 0, CM_REPORT_SIZE);
    data[0] = 0xD3;
    data[1] = 0xAC;
    data[2] = 1;
    data[3] = opcode;
    write32(data + 4, request_id);
    data[8] = status;
    if (opcode == CM_CAPABILITIES) {
        static const uint8_t uid[] = {0x89, 0x36, 0x2A, 0xC7, 0xFA, 0xD8, 0x89, 0x45};
        data[9] = CM_LAYER_COUNT;
        data[10] = 0x0F;
        data[11] = 2;
        memcpy(data + 12, uid, sizeof(uid));
        write32(data + 20, CM_REGISTRY_HASH);
        write32(data + 24, 0x434D0001u);
    } else {
        data[9] = s->selection.mode;
        data[10] = s->selection.layer;
        data[11] = (s->picker ? 1 : 0) | (s->mirror_holds ? 2 : 0) | (s->pending ? 4 : 0) | (s->session ? 8 : 0);
        write32(data + 12, s->session);
        write32(data + 16, s->epoch);
        write32(data + 20, s->revision);
        uint16_t mask = cm_layer_mask(s);
        data[24] = mask;
        data[25] = mask >> 8;
        data[26] = CM_LAYER_COUNT;
        data[27] = 0x0F;
        write32(data + 28, CM_REGISTRY_HASH);
    }
}

bool cm_report(cm_protocol_t *p, cm_state_t *s, uint8_t *data, uint8_t length, uint32_t now, bool quiescent) {
    if (length < 2 || data[0] != 0xD3 || data[1] != 0x43) return false;
    if (length != CM_REPORT_SIZE) return true;
    uint8_t request[CM_REPORT_SIZE];
    memcpy(request, data, sizeof(request));
    uint8_t opcode = data[3];
    uint32_t id = read32(data + 4), session = read32(data + 8);
    uint32_t epoch = read32(data + 12), sequence = read32(data + 16);
    cm_status_t status = CM_OK;
    if (data[2] != 1) status = CM_UNSUPPORTED_VERSION;
    else if (!id || opcode < CM_CAPABILITIES || opcode > CM_CLOSE) status = CM_BAD_REQUEST;
    for (uint8_t i = 21; i < CM_REPORT_SIZE; ++i) {
        if (data[i]) status = CM_BAD_REQUEST;
    }
    if ((opcode == CM_CAPABILITIES && session) || (opcode != CM_CAPABILITIES && !session) ||
        (opcode != CM_CONTEXT && (epoch || sequence || data[20])) ||
        (opcode == CM_CONTEXT && (!epoch || !sequence))) status = CM_BAD_REQUEST;
    if (status != CM_OK) {
        reply(data, opcode, id, status, s);
        return true;
    }
    if (opcode == CM_CAPABILITIES) {
        reply(data, opcode, id, CM_OK, s);
        return true;
    }
    cm_tick(s, now, quiescent);
    if (cm_configuration_busy(s, now)) status = CM_BUSY_CONFIGURATION;
    else if (p->cached && p->revision == s->revision && memcmp(p->request, request, sizeof(request)) == 0) {
        memcpy(data, p->response, CM_REPORT_SIZE);
        return true;
    } else {
        switch (opcode) {
            case CM_OPEN: status = cm_open(s, session, now); break;
            case CM_STATE: status = cm_renew(s, session, now); break;
            case CM_CONTEXT: status = cm_context(s, session, epoch, sequence, data[20], now, quiescent); break;
            case CM_CLOSE: status = cm_close(s, session); break;
        }
    }
    reply(data, opcode, id, status, s);
    if (status == CM_OK || status == CM_DEFERRED) {
        memcpy(p->request, request, CM_REPORT_SIZE);
        memcpy(p->response, data, CM_REPORT_SIZE);
        p->revision = s->revision;
        p->cached = true;
    }
    return true;
}
