#!/usr/bin/env python3
"""Test the generated cleanup helper with temporary state and a fake Docker CLI."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

try:
    import fcntl
except ImportError:
    fcntl = None


INSTALLER = Path(__file__).resolve().parents[1] / "docker_install.sh"
HELPER = INSTALLER.read_text().split("<<'CACHE_PRUNE'\n", 1)[1].split("\nCACHE_PRUNE\n", 1)[0]
INTERVAL = 10 * 24 * 60 * 60


@unittest.skipUnless(fcntl and shutil.which("bash") and shutil.which("flock"), "Linux Bash/flock required")
class CachePruneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.state.mkdir()
        self.stamp = self.state / "last-success"
        self.commands = self.root / "commands"
        docker = self.root / "docker"
        docker.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$PRUNE_TEST_COMMANDS"\nexit "${PRUNE_TEST_EXIT:-0}"\n')
        docker.chmod(0o755)
        self.helper = self.root / "prune.sh"
        self.helper.write_text(HELPER.replace("/var/lib/docker-build-cache-prune", str(self.state))
                               .replace("/usr/bin/docker", str(docker)))

    def run_helper(self, *args, failure=False):
        env = dict(os.environ, PRUNE_TEST_COMMANDS=str(self.commands), PRUNE_TEST_EXIT="1" if failure else "0")
        return subprocess.run(["bash", str(self.helper), *args], env=env, capture_output=True, text=True)

    def assert_no_prune(self):
        self.assertFalse(self.commands.exists())

    def test_first_install_initializes_without_cleaning(self):
        before = int(time.time())
        result = self.run_helper("--initialize")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreaterEqual(int(self.stamp.read_text()), before)
        self.assert_no_prune()

    def test_install_again_keeps_existing_schedule(self):
        previous = str(int(time.time()) - 5 * 86400)
        self.stamp.write_text(previous)
        result = self.run_helper("--initialize")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stamp.read_text(), previous)
        self.assert_no_prune()

    def test_not_due_before_ten_full_days(self):
        self.stamp.write_text(str(int(time.time()) - INTERVAL + 60))
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_no_prune()

    def test_due_prunes_only_old_build_cache_and_resets_interval(self):
        self.stamp.write_text(str(int(time.time()) - INTERVAL - 60))
        before = int(time.time())
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands.read_text().splitlines(), ["builder prune -af --filter until=168h"])
        self.assertGreaterEqual(int(self.stamp.read_text()), before)
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.commands.read_text().splitlines()), 1)

    def test_failure_keeps_timestamp_and_next_check_retries(self):
        previous = str(int(time.time()) - INTERVAL - 60)
        self.stamp.write_text(previous)
        self.assertNotEqual(self.run_helper(failure=True).returncode, 0)
        self.assertEqual(self.stamp.read_text(), previous)
        self.assertEqual(self.run_helper().returncode, 0)
        self.assertEqual(len(self.commands.read_text().splitlines()), 2)

    def test_concurrent_check_skips_without_pruning(self):
        self.stamp.write_text(str(int(time.time()) - INTERVAL - 60))
        with (self.state / "lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_no_prune()

    def test_invalid_timestamp_does_not_prune(self):
        self.stamp.write_text("invalid")
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertEqual(self.stamp.read_text(), "invalid")
        self.assert_no_prune()


if __name__ == "__main__":
    unittest.main(verbosity=2)
