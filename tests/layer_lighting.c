// Host test of the actual output adapter; only QMK/WS2812 I/O is substituted.
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define HAS_ANY_FLAGS(a, b) ((a) & (b))
#define RGB_MATRIX_MAXIMUM_BRIGHTNESS 50
#define RGB_MATRIX_TIMEOUT 1000
#define WS2812_LED_COUNT 46

typedef struct { uint8_t h, s, v; } hsv_t;
typedef struct { uint8_t r, g, b; } rgb_t;
typedef struct {
    void (*init)(void);
    void (*set_color)(int, uint8_t, uint8_t, uint8_t);
    void (*set_color_all)(uint8_t, uint8_t, uint8_t);
    void (*flush)(void);
} rgb_matrix_driver_t;
static uint32_t layer_state, default_layer_state, idle;
static bool enabled = true, suspended, left = true;
static uint8_t brightness = 40, flags = 4;
#define RGB_MATRIX_SPLIT {23, 23}
static struct { uint8_t flags[46]; } g_led_config;
static rgb_t leds[46], output[46];
static uint8_t get_highest_layer(uint32_t state) { return state ? 31 - __builtin_clz(state) : 0; }
static bool rgb_matrix_is_enabled(void) { return enabled; }
static bool rgb_matrix_get_suspend_state(void) { return suspended; }
static uint8_t rgb_matrix_get_val(void) { return brightness; }
static uint8_t rgb_matrix_get_flags(void) { return flags; }
static bool is_keyboard_left(void) { return left; }
static uint32_t last_input_activity_elapsed(void) { return idle; }
// Encode HSV into RGB for observability; QMK colour conversion is not under test.
static rgb_t hsv_to_rgb(hsv_t hsv) { return (rgb_t){hsv.h, hsv.s, hsv.v}; }
static void ws2812_init(void) {}
static void ws2812_set_color(int i, uint8_t r, uint8_t g, uint8_t b) {
    assert(i >= 0 && i < 46);
    leds[i] = (rgb_t){r, g, b};
}
// The selected RP2040 vendor driver copies to a separate DMA buffer here.
static void ws2812_flush(void) { memcpy(output, leds, sizeof(output)); }
#include "../keyboards/crkbd/vial-kb/vial-qmk/keymaps/vial/layer_lighting.h"

static void frame(uint8_t hue, bool overlay) {
    // Deliberately do NOT repaint: models a sparse effect such as Raindrops.
    rgb_matrix_driver.flush();
    for (unsigned i = 0; i < 46; ++i) {
        bool painted = overlay && i < 23 &&
            (g_led_config.flags[i + (left ? 0 : 23)] & flags);
        assert(output[i].r == (painted ? hue : 7));
        assert(output[i].g == (painted ? 255 : 7));
        assert(output[i].b == (painted ? MIN(brightness, 50) : 7));
        assert(leds[i].r == 7 && leds[i].g == 7 && leds[i].b == 7);
    }
}

int main(void) {
    memset(g_led_config.flags, 4, sizeof(g_led_config.flags));
    rgb_matrix_driver.init();
    rgb_matrix_driver.set_color_all(7, 7, 7);
    default_layer_state = 1;
    frame(0, false);
    layer_state = 1 << 1; frame(85, true); // TG(1)
    layer_state |= 1 << 2; frame(191, true);
    layer_state |= 1 << 3; frame(30, true); // tri-layer adjust
    layer_state &= ~(1 << 3); frame(191, true);
    layer_state &= ~(1 << 2); frame(85, true);
    layer_state = 0; frame(0, false); // toggle-off restores sparse effect
    layer_state = 1 << 2; frame(191, true); // FN_MO23 alone
    layer_state = 0; frame(0, false); // release restores effect
    default_layer_state = 1 << 3;
    layer_state = 1 << 1; frame(30, true); // highest default wins
    default_layer_state = 1 << 1;
    layer_state = 0; frame(85, true);
    layer_state = 1 << 4; frame(0, false);
    layer_state = 1 << 5; frame(0, false);
    layer_state = 1u << 31; frame(0, false); // safe outside palette
    default_layer_state = 1;
    layer_state = 1 << 2;
    brightness = 255; frame(191, true);
    brightness = 0; frame(191, true);
    enabled = false; frame(0, false);
    enabled = true; suspended = true; frame(0, false);
    suspended = false; idle = 1001; frame(0, false);
    idle = 0; brightness = 17; frame(191, true);
    g_led_config.flags[0] = 0; frame(191, true);
    left = false; g_led_config.flags[25] = 0; frame(191, true);
    layer_state = 0; frame(0, false);
    // A sparse effect can continue changing individual LEDs after the overlay.
    rgb_matrix_driver.set_color(2, 9, 10, 11);
    rgb_matrix_driver.flush();
    assert(output[2].r == 9 && output[2].g == 10 && output[2].b == 11);
    assert(default_layer_state == 1 && enabled && !suspended && brightness == 17);
    puts("layer lighting: overlap, defaults, release/toggle restoration, sparse effects, off/suspend/timeout, cap, flags and both halves passed");
}
