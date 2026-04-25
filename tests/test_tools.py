import tempfile
import unittest
from pathlib import Path

from kautuk_offline_agent.tools import LocalTooling


class ToolingTests(unittest.TestCase):
    def test_run_command_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tooling = LocalTooling(Path(tmp))
            result = tooling.run_command("python -c \"import time; time.sleep(2)\"", timeout_seconds=1)
            self.assertTrue(result.timed_out)
            self.assertEqual(result.returncode, 124)

    def test_blocks_destructive_command_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tooling = LocalTooling(Path(tmp))
            result = tooling.run_command("rm -rf /tmp/something")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Blocked potentially destructive command", result.stderr)
