import os
import sys


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from wechat_digest_app.gui import launch


if __name__ == "__main__":
    smoke = "--smoke-test" in sys.argv
    raise SystemExit(launch(smoke_test=smoke))
