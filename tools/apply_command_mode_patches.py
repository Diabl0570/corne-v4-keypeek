#!/usr/bin/env python3
"""Apply the reviewed command-mode hooks to the exact pinned Vial source."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PATCHES = ROOT / "patches/command-mode"


def run(source, *args):
    return subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True).stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def apply(source, check=False):
    manifest = json.loads((PATCHES / "manifest.json").read_text())
    patch = PATCHES / "hooks.patch"
    if digest(patch.read_bytes()) != manifest["patch_sha256"]:
        raise ValueError("Reviewed patch hash mismatch")
    if run(source, "rev-parse", "HEAD").decode().strip() != manifest["source_commit"]:
        raise ValueError("Vial source commit does not match the reviewed pin")
    paths = set(manifest["files"])
    dirty = set(run(source, "diff", "HEAD", "--name-only", "--ignore-submodules=none").decode().splitlines())
    if dirty - paths:
        raise ValueError("Unexpected tracked Vial changes: " + ", ".join(sorted(dirty - paths)))
    untracked = run(source, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    unexpected = [path for path in untracked if path and not path.startswith("keyboards/tmp/")]
    if unexpected:
        raise ValueError("Unexpected untracked Vial files: " + ", ".join(sorted(unexpected)))
    states = set()
    for path, hashes in manifest["files"].items():
        actual = digest((source / path).read_bytes())
        matches = [state for state, expected in hashes.items() if actual == expected]
        if len(matches) != 1:
            raise ValueError("Unexpected source content: " + path)
        states.add(matches[0])
    if len(states) != 1:
        raise ValueError("Partially patched source; restore the reviewed pin before applying")
    state = states.pop()
    if state == "patched":
        return "already applied"
    run(source, "apply", "--check", str(patch))
    if check:
        return "checked, ready to apply"
    run(source, "apply", str(patch))
    for path, hashes in manifest["files"].items():
        if digest((source / path).read_bytes()) != hashes["patched"]:
            raise ValueError("Post-apply verification failed: " + path)
    return "applied and verified"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "src/vial-kb/vial-qmk")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = apply(args.source.resolve(), args.check)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print("Command-mode patch refused: " + str(error), file=sys.stderr)
        return 1
    print("Command-mode hooks " + result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
