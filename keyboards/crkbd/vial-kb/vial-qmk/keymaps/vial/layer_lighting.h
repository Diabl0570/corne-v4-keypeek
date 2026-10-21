// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// An overlay, never an RGB configuration change. Zero saturation means that
// this layer leaves the selected global effect visible (base/reserved layers).
#ifdef COMMAND_MODE_ENABLE
#    include "command_registry.h"
static const hsv_t layer_indicators[] = CM_LAYER_PALETTE;
#else
static const hsv_t layer_indicators[] = {
    [0] = {0, 0, 0},
    [1] = {85, 255, 0},  // green: numbers/navigation
    [2] = {191, 255, 0}, // purple: symbols
    [3] = {30, 255, 0},  // amber: maintenance
    [4] = {0, 0, 0},
    [5] = {0, 0, 0},
};
#endif

// Driver indices are local to each half. Keep the effect's unmodified buffer:
// sparse effects (e.g. Raindrops) do not repaint every LED on every frame.
static rgb_t effect_colors[WS2812_LED_COUNT];
static const uint8_t split_counts[] = RGB_MATRIX_SPLIT;

static void layer_lighting_set_color(int index, uint8_t r, uint8_t g, uint8_t b) {
    effect_colors[index] = (rgb_t){r, g, b};
    ws2812_set_color(index, r, g, b);
}

static void layer_lighting_set_color_all(uint8_t r, uint8_t g, uint8_t b) {
    for (uint8_t i = 0; i < WS2812_LED_COUNT; ++i) {
        layer_lighting_set_color(i, r, g, b);
    }
}

static void layer_lighting_flush(void) {
    const uint8_t layer = get_highest_layer(layer_state | default_layer_state);
    bool overlay = rgb_matrix_is_enabled() && !rgb_matrix_get_suspend_state() &&
                   layer < ARRAY_SIZE(layer_indicators) && layer_indicators[layer].s;
#if RGB_MATRIX_TIMEOUT > 0
    overlay = overlay && last_input_activity_elapsed() <= (uint32_t)RGB_MATRIX_TIMEOUT;
#endif
    if (overlay) {
        hsv_t hsv = layer_indicators[layer];
        hsv.v = MIN(rgb_matrix_get_val(), RGB_MATRIX_MAXIMUM_BRIGHTNESS);
        const rgb_t rgb = hsv_to_rgb(hsv);
        const uint8_t offset = is_keyboard_left() ? 0 : split_counts[0];
        const uint8_t count = split_counts[is_keyboard_left() ? 0 : 1];
        for (uint8_t i = 0; i < count; ++i) {
            if (HAS_ANY_FLAGS(g_led_config.flags[i + offset], rgb_matrix_get_flags())) {
                ws2812_set_color(i, rgb.r, rgb.g, rgb.b);
            }
        }
    }

    // The selected RP2040 vendor implementation copies colours into its DMA
    // buffer before returning. Restoring the effect buffer here is safe.
    ws2812_flush();
    if (overlay) {
        for (uint8_t i = 0; i < WS2812_LED_COUNT; ++i) {
            const rgb_t rgb = effect_colors[i];
            ws2812_set_color(i, rgb.r, rgb.g, rgb.b);
        }
    }
}

const rgb_matrix_driver_t rgb_matrix_driver = {
    .init = ws2812_init,
    .set_color = layer_lighting_set_color,
    .set_color_all = layer_lighting_set_color_all,
    .flush = layer_lighting_flush,
};
