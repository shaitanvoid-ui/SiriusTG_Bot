from __future__ import annotations

import subprocess
import sys


def test_complete_rich_navigation_and_reward_flow(tmp_path):
    result = subprocess.run([sys.executable, "-m", "tests.rich_flow_scenario", str(tmp_path)],
                            capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Dispatcher flow passed" in result.stdout
