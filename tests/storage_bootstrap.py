#!/usr/bin/env python3
"""Run the real patched bootstrap and pinned EEPROM/settings/boot functions on fake EEPROM."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PIN = "dd43959ae5c08d8a28d38a1acf7b04e86b14a344"
KEYMAP = ROOT / "keyboards/crkbd/vial-kb/vial-qmk/keymaps/vial"


def run(*args, **kwargs):
    result = subprocess.run(args, text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result


def function(text, name):
    match = re.search(r"(?m)^[\w *]+\b" + name + r"\([^\n]*\) \{", text)
    if not match:
        raise AssertionError("Missing source function " + name)
    start = match.start()
    brace = text.index("{", match.start())
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end] + "\n"


def without_includes(text):
    return re.sub(r'^\s*#\s*include[^\n]*\n', '\n', text, flags=re.M)


def source_piece(source, path, names):
    text = (source / path).read_text()
    return '\n'.join(function(text, name) for name in names)


def refused(source):
    result = subprocess.run(["python3", str(ROOT / "tools/apply_command_mode_patches.py"), "--source", str(source)], capture_output=True, text=True)
    assert result.returncode != 0, result.stdout
    return result.stderr


def check_patcher(source):
    command = ["python3", str(ROOT / "tools/apply_command_mode_patches.py"), "--source", str(source)]
    assert "ready" in run(*command, "--check").stdout
    assert not run("git", "-C", str(source), "diff", "--name-only").stdout
    original = (source / "quantum/via.c").read_bytes()
    (source / "quantum/via.c").write_bytes(original + b"\n")
    assert "Unexpected source content" in refused(source)
    assert (source / "quantum/keyboard.c").read_bytes() == run("git", "-C", str(source), "show", "HEAD:quantum/keyboard.c").stdout.encode()
    (source / "quantum/via.c").write_bytes(original)
    unexpected = source / "quantum/unreviewed.h"
    unexpected.write_text("unreviewed source\n")
    assert "Unexpected untracked" in refused(source)
    unexpected.unlink()
    assert "applied and verified" in run(*command).stdout
    assert "already applied" in run(*command).stdout
    assert "already applied" in run(*command, "--check").stdout
    patched = (source / "quantum/via.c").read_bytes()
    (source / "quantum/via.c").write_bytes(original)
    assert "Partially patched" in refused(source)
    (source / "quantum/via.c").write_bytes(patched)
    unrelated = source / "quantum/qmk_settings.c"
    old = unrelated.read_bytes()
    unrelated.write_bytes(old + b"\n")
    assert "Unexpected tracked" in refused(source)
    unrelated.write_bytes(old)
    run("git", "-C", str(source), "-c", "user.name=Fixture", "-c", "user.email=fixture@localhost", "commit", "--allow-empty", "-m", "fixture pin mismatch")
    assert "source commit" in refused(source)
    run("git", "-C", str(source), "reset", "--soft", PIN)


def prepare(source, output, settings):
    for name in ("quantum.h", "dynamic_keymap.h", "keymap_introspection.h", "via.h", "vial.h", "compiler_support.h", "keycodes.h", "eeprom.h", "nvm_dynamic_keymap.h", "nvm_eeprom_eeconfig_internal.h", "nvm_eeprom_via_internal.h", "encoder.h"):
        (output / name).write_text("#pragma once\n")
    (output / "quantum/nvm").mkdir(parents=True)
    (output / "quantum/nvm/nvm_eeconfig.h").write_text("#pragma once\n")
    (output / "qmk_settings.h").write_text((source / "quantum/qmk_settings.h").read_text().replace('#include "quantum/action.h"', ''))
    vial = (source / "quantum/vial.h").read_text()
    structs = []
    for name in ("vial_tap_dance_entry_t", "vial_combo_entry_t", "vial_key_override_entry_t", "vial_alt_repeat_key_entry_t"):
        end = vial.index("} " + name + ";") + len("} " + name + ";")
        start = vial.rfind("typedef struct {", 0, end)
        structs.append(vial[start:end])
    (output / "vial_types.inc").write_text('\n'.join(structs))
    core = (source / "quantum/nvm/eeprom/nvm_eeprom_eeconfig_internal.h").read_text()
    (output / "core_offsets.inc").write_text(without_includes(core))
    (output / "via_offsets.inc").write_text((source / "quantum/nvm/eeprom/nvm_eeprom_via_internal.h").read_text())
    (output / "nvm.inc").write_text(without_includes((source / "quantum/nvm/eeprom/nvm_dynamic_keymap.c").read_text()))
    (output / "settings.inc").write_text(without_includes((source / "quantum/qmk_settings.c").read_text()))
    (output / "dynamic.inc").write_text(source_piece(source, "quantum/dynamic_keymap.c", ["dynamic_keymap_get_qmk_settings", "dynamic_keymap_set_qmk_settings", "dynamic_keymap_set_keycode", "dynamic_keymap_set_encoder", "dynamic_keymap_set_tap_dance", "dynamic_keymap_set_combo", "dynamic_keymap_set_key_override", "dynamic_keymap_set_alt_repeat_key", "dynamic_keymap_macro_reset"]))
    (output / "via.inc").write_text(source_piece(source, "quantum/via.c", ["via_eeprom_is_valid", "via_eeprom_set_valid", "via_get_layout_options", "via_set_layout_options", "eeconfig_init_via", "via_init"]))
    (output / "core_nvm.inc").write_text(source_piece(source, "quantum/nvm/eeprom/nvm_eeconfig.c", ["nvm_eeconfig_is_enabled", "nvm_eeconfig_enable"]))
    (output / "core.inc").write_text(source_piece(source, "quantum/eeconfig.c", ["eeconfig_init_quantum", "eeconfig_init", "eeconfig_enable", "eeconfig_is_enabled"]))
    (output / "boot.inc").write_text(source_piece(source, "quantum/keyboard.c", ["keyboard_setup", "quantum_init"]))
    (output / "vial.inc").write_text(source_piece(source, "quantum/vial.c", ["vial_init"]))
    for name in ("storage_bootstrap.c", "storage_bootstrap.h"):
        (output / name).write_bytes((KEYMAP / name).read_bytes())
    fixture_settings = settings
    (output / "command_settings.h").write_bytes(fixture_settings.read_bytes())
    (output / "fixture.c").write_bytes((ROOT / "tests/storage_bootstrap/fixture.c").read_bytes())
    tapping = (source / "quantum/action_tapping.c").read_text()
    (output / "idle.inc").write_text(function(tapping, "action_tapping_is_idle"))
    action = function((source / "quantum/action.c").read_text(), "action_exec")
    assert action.index("command_mode_pre_action(event)") < action.index("get_event_keycode") < action.index("process_hand_swap")
    via = function((source / "quantum/via.c").read_text(), "raw_hid_receive")
    assert via.index("command_mode_configuration_activity()") < via.index("vial_unlock_in_progress") < via.index("switch")
    hook = via[:via.index("    uint8_t *command_id")].replace("void raw_hid_receive", "void admission_fixture") + "}\n"
    (output / "admission.inc").write_text(hook)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "src/vial-kb/vial-qmk")
    parser.add_argument("--settings", type=Path, default=ROOT / "tests/storage_bootstrap/settings.h")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="command-mode-storage-") as temporary:
        output = Path(temporary)
        source = output / "pinned"
        run("git", "clone", "--shared", "--no-checkout", "--quiet", str(args.source), str(source))
        paths = ["quantum/" + name for name in ("keyboard.c", "via.c", "action.c", "action_tapping.c", "action_tapping.h", "eeconfig.c", "qmk_settings.c", "qmk_settings.h", "dynamic_keymap.c", "vial.c", "vial.h", "nvm/eeprom/nvm_dynamic_keymap.c", "nvm/eeprom/nvm_eeprom_eeconfig_internal.h", "nvm/eeprom/nvm_eeprom_via_internal.h", "nvm/eeprom/nvm_eeconfig.c")]
        run("git", "-C", str(source), "sparse-checkout", "set", "--no-cone", *["/" + p for p in paths])
        run("git", "-C", str(source), "checkout", "--quiet", "--detach", PIN)
        check_patcher(source)
        build = output / "fixture"
        build.mkdir()
        prepare(source, build, args.settings)
        run("clang", "-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", "-Wno-sign-compare", "-Wno-int-to-pointer-cast", "-Wno-pointer-to-int-cast", "-I", str(build), str(build / "fixture.c"), "-o", str(build / "test"))
        print(run(str(build / "test")).stdout, end="")
        print("Pinned patch checks, pin/content mismatch rejection, partial-state rejection, and idempotence passed")


if __name__ == "__main__":
    main()
