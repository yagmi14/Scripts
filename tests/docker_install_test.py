#!/usr/bin/env python3
"""Exercise daemon configuration in temporary directories; never install Docker."""

import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


INSTALLER = Path(__file__).resolve().parents[1] / "docker_install.sh"
CONFIG_CODE = INSTALLER.read_text().split("<<'PYTHON'\n", 1)[1].split("\nPYTHON\n", 1)[0]


class DockerLoggingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name) / "docker" / "daemon.json"

    def write_config(self, value):
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text(json.dumps(value))

    def execute_config(self, validator=None):
        with patch.object(sys, "argv", ["-", str(self.config)]), contextlib.redirect_stdout(io.StringIO()):
            if validator is None:
                exec(compile(CONFIG_CODE, str(INSTALLER), "exec"), {})
            else:
                with patch("subprocess.run", side_effect=validator):
                    exec(compile(CONFIG_CODE, str(INSTALLER), "exec"), {})

    def validate_candidate(self, args, *, check):
        self.assertEqual(args[:3], ["dockerd", "--validate", "--config-file"])
        self.assertTrue(check)
        candidate = json.loads(Path(args[3]).read_text())
        self.assertEqual(candidate["log-driver"], "json-file")
        self.assertEqual(candidate["log-opts"]["max-size"], "50m")
        self.assertEqual(candidate["log-opts"]["max-file"], "5")
        return subprocess.CompletedProcess(args, 0)

    def test_new_install(self):
        self.execute_config(self.validate_candidate)
        self.assertEqual(json.loads(self.config.read_text()), {
            "log-driver": "json-file", "log-opts": {"max-size": "50m", "max-file": "5"},
        })
        self.assertEqual(list(self.config.parent.glob("daemon.json.backup.*")), [])

    def test_preserves_existing_settings_and_backup(self):
        original = {
            "registry-mirrors": ["https://mirror.example.test"], "dns": ["1.1.1.1"],
            "log-driver": "json-file", "log-opts": {"labels": "production", "max-size": "1g"},
        }
        self.write_config(original)
        before = self.config.read_bytes()
        self.execute_config(self.validate_candidate)
        result = json.loads(self.config.read_text())
        self.assertEqual(result["registry-mirrors"], original["registry-mirrors"])
        self.assertEqual(result["dns"], original["dns"])
        self.assertEqual(result["log-opts"]["labels"], "production")
        backups = list(self.config.parent.glob("daemon.json.backup.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), before)

    def test_drops_options_specific_to_another_driver(self):
        self.write_config({"log-driver": "syslog", "log-opts": {"syslog-address": "udp://127.0.0.1:514"}})
        self.execute_config(self.validate_candidate)
        self.assertEqual(json.loads(self.config.read_text())["log-opts"], {"max-size": "50m", "max-file": "5"})

    def test_repeated_run_does_not_rewrite_or_create_another_backup(self):
        self.execute_config(self.validate_candidate)
        before = self.config.stat().st_mtime_ns
        self.execute_config(self.validate_candidate)
        self.assertEqual(self.config.stat().st_mtime_ns, before)
        self.assertEqual(list(self.config.parent.glob("daemon.json.backup.*")), [])

    def test_rejects_malformed_or_wrong_shape_without_overwriting(self):
        for value in ["{broken", "[]", '{"log-opts": []}']:
            with self.subTest(value=value):
                self.config.parent.mkdir(parents=True, exist_ok=True)
                self.config.write_text(value)
                with self.assertRaises((ValueError, SystemExit)):
                    self.execute_config(self.validate_candidate)
                self.assertEqual(self.config.read_text(), value)
                self.assertEqual(sorted(p.name for p in self.config.parent.iterdir()), ["daemon.json"])

    def test_failed_validation_preserves_existing_configuration(self):
        self.write_config({"dns": ["1.1.1.1"]})
        before = self.config.read_bytes()
        with self.assertRaises(subprocess.CalledProcessError):
            self.execute_config(lambda args, **_: (_ for _ in ()).throw(subprocess.CalledProcessError(1, args)))
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.config.parent.iterdir()), ["daemon.json"])

    def test_failed_validation_does_not_install_new_configuration(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.execute_config(lambda args, **_: (_ for _ in ()).throw(subprocess.CalledProcessError(1, args)))
        self.assertFalse(self.config.exists())
        self.assertEqual(list(self.config.parent.iterdir()), [])

    @unittest.skipUnless(shutil.which("dockerd"), "dockerd is not installed")
    def test_real_dockerd_validation(self):
        self.write_config({"dns": ["1.1.1.1"]})
        self.execute_config()
        result = json.loads(self.config.read_text())
        self.assertEqual(result["dns"], ["1.1.1.1"])
        self.assertEqual(result["log-opts"], {"max-size": "50m", "max-file": "5"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
