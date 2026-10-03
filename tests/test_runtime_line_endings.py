"""Validate the installed image entrypoint, including Windows Git exports."""
from pathlib import Path
import subprocess


def test_installed_runtime_entrypoint_is_valid_linux_shell():
    entrypoint = Path("/usr/local/bin/sirius-entrypoint")
    assert b"\r" not in entrypoint.read_bytes(), "CRLF breaks Linux shell entrypoints"
    result = subprocess.run(["/bin/sh", "-n", str(entrypoint)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
