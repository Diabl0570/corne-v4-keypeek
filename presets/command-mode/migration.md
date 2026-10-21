# Exact preset migration

Input: `backups/2026-10-21-live/corne-v4.1-live-2026-10-21-1631.vil`.

Baseline16 appends layers6..15 and their encoders. Every original layer/encoder cell and every other JSON field is identical. Experimental16 differs from baseline16 at exactly one path:

- `layout[0][3][5]`: `KC_SPACE` → `USER03`, tap Space / hold Mirror.

No home-row timing, Tap Dance, combo, macro, override or core setting changes. Sixteen layers leave815 macro bytes; this source has16 empty macro slots. Future flashing requires the explicit upgrade/import/readback procedure. These files have not been loaded onto the keyboard.
