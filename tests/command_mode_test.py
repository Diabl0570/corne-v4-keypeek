#!/usr/bin/env python3
"""Run the reducer and the pinned QMK event/tapping/cache path under UBSan."""

import argparse
import pathlib
import re
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
KEYMAP = ROOT / "keyboards/crkbd/vial-kb/vial-qmk/keymaps/vial"


def function(source, name):
    match = re.search(r"^(?:[\w*]+\s+)+" + re.escape(name) + r"\([^;]*?\)\s*\{", source, re.M)
    if not match:
        raise RuntimeError(f"Pinned source function missing: {name}")
    start = source.index("{", match.start())
    depth = 1
    end = start + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[match.start():end] + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qmk-source", type=pathlib.Path, default=ROOT / "src/vial-kb/vial-qmk")
    args = parser.parse_args()
    pin = subprocess.check_output(["git", "-C", str(args.qmk_source), "rev-parse", "HEAD"], text=True).strip()
    assert pin == "dd43959ae5c08d8a28d38a1acf7b04e86b14a344", "Unexpected Vial source pin"
    quantum = args.qmk_source / "quantum"
    action = (quantum / "action.c").read_text()
    layer = (quantum / "action_layer.c").read_text()
    tapping = (quantum / "action_tapping.c").read_text()
    quantum_source = (quantum / "quantum.c").read_text()
    assert "command_mode_pre_action(event)" in action, "Apply checked production source hooks first"
    assert "action_tapping_is_idle(void)" in tapping, "Apply checked production source hooks first"
    with tempfile.TemporaryDirectory(prefix="command-mode-test-") as tmp:
        work = pathlib.Path(tmp)
        shutil.copy(ROOT / "tests/command_mode_qmk_shim.h", work)
        for name in ["action_code.h", "modifiers.h", "keycodes.h", "action_tapping.h"]:
            shutil.copy(quantum / name, work / name)
        for name in ["action.h", "action_layer.h", "action_util.h", "keycode.h", "quantum_keycodes.h", "timer.h"]:
            (work / name).write_text('#include "command_mode_qmk_shim.h"\n')
        (work / "qmk_tapping.c").write_text('#include "command_mode_qmk_shim.h"\n' + tapping)
        wrappers = '#include "command_mode_qmk_shim.h"\n#include "command_qmk.h"\n#include "action_tapping.h"\n'
        wrappers += "bool disable_action_cache, swap_hands, swap_held;\n"
        wrappers += "uint8_t source_layers_cache[7][MAX_LAYER_BITS], encoder_source_layers_cache[1][MAX_LAYER_BITS];\n"
        for name in ["action_exec", "should_swap_hands", "set_swap_hands_state", "process_hand_swap", "swap_hands_on", "swap_hands_off", "is_swap_hands_on", "process_record", "process_record_handler", "is_tap_record", "is_tap_action"]:
            wrappers += function(action, name)
        for name in ["update_source_layers_cache_impl", "read_source_layers_cache_impl", "update_source_layers_cache", "read_source_layers_cache", "store_or_get_action", "layer_switch_get_layer", "layer_switch_get_action"]:
            wrappers += function(layer, name)
        for name in ["get_record_keycode", "get_event_keycode", "pre_process_record_quantum", "process_record_quantum"]:
            wrappers += function(quantum_source, name)
        (work / "qmk_wrappers.c").write_text(wrappers)
        command = ["clang", "-std=gnu11", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", "-Wno-unused-function", "-Wno-missing-field-initializers", "-fsanitize=undefined", "-fno-sanitize-recover=all", "-g", "-I", str(work), "-I", str(KEYMAP), '-DQMK_KEYBOARD_H="command_mode_qmk_shim.h"', "-include", str(work / "command_mode_qmk_shim.h"), str(work / "qmk_wrappers.c"), str(work / "qmk_tapping.c"), str(KEYMAP / "command_state.c"), str(KEYMAP / "command_protocol.c"), str(KEYMAP / "command_qmk.c"), str(ROOT / "tests/command_mode.c"), "-o", str(work / "test")]
        subprocess.run(command, check=True)
        subprocess.run([str(work / "test")], check=True)
        print("QMK source pin verified: " + pin, flush=True)


if __name__ == "__main__":
    main()
