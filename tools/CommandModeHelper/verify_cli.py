"""Exercise only mock CLI paths. Build the release executable before running."""

from pathlib import Path
import signal
import subprocess
import time


def main():
    binary = Path(__file__).resolve().parent / ".build/release/command-mode-helper"
    commands = "status\npause\nstatus\nresume\nstatus\ndisable\nstatus\nquit\n"
    result = subprocess.run(
        [binary, "dry-run", "--seconds", "5", "--simulate-auto"],
        input=commands,
        text=True,
        capture_output=True,
        timeout=8,
        check=True,
    )
    assert "phase=paused(user)" in result.stdout, result.stdout
    assert "mode=manual" in result.stdout, result.stdout
    assert "phase=stopped" in result.stdout, result.stdout
    assert "native HID objects=0" in result.stdout, result.stdout
    print("mock start/status/pause/resume/disable/quit passed")

    process = subprocess.Popen(
        [binary, "dry-run", "--seconds", "10"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(0.8)
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=3)
        assert process.returncode == 0, stderr
        assert "phase=stopped" in stdout, stdout
        assert "native HID objects=0" in stdout, stdout
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()
    print("mock SIGINT cleanup passed")

    unsupported = subprocess.run(
        [binary, "capability", "dictation"], text=True, capture_output=True, timeout=3
    )
    assert unsupported.returncode == 1
    assert "unsupported action" in unsupported.stderr
    print("unsupported capability exits 1")


if __name__ == "__main__":
    main()
