import os
import subprocess
import sys
import unittest
from unittest import mock


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


class SmokeTests(unittest.TestCase):
    def test_digest_imports(self):
        import digest

        self.assertTrue(callable(digest.main))

    def test_backend_preview_output_path(self):
        from wechat_digest_app import backend

        fake_cfg = {"decrypted_dir": "", "output_dir": os.path.join(ROOT_DIR, "output"), "known": {}}
        with mock.patch("digest.load_config", return_value=fake_cfg):
            path = backend.preview_output_path("Demo Group", "2026-04-24")
        self.assertTrue(path.endswith(os.path.join("output", "Demo Group", "2026-04-24.md")))

    def test_gui_smoke(self):
        env = dict(os.environ)
        env["QT_QPA_PLATFORM"] = "offscreen"
        proc = subprocess.run(
            [sys.executable, "run_gui.py", "--smoke-test"],
            cwd=ROOT_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            raise AssertionError(proc.stderr or proc.stdout)


if __name__ == "__main__":
    unittest.main()
