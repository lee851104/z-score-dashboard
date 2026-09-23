"""Check built resources and run the installed layout outside the checkout."""

import argparse
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", default="dist")
    args = parser.parse_args()
    wheels = sorted(Path(args.directory).glob("zscore_dashboard-*.whl"))
    if len(wheels) != 1:
        raise SystemExit("Expected exactly one zscore_dashboard wheel")
    with tempfile.TemporaryDirectory() as directory:
        with zipfile.ZipFile(wheels[0]) as archive:
            required = {
                "zscore_dashboard/data/market.py",
                "zscore_dashboard/features/indicators.py",
                "zscore_dashboard/serving/templates/index.html",
                "zscore_dashboard/dashboard.toml",
            }
            if not required.issubset(archive.namelist()):
                raise SystemExit("Wheel is missing application resources")
            archive.extractall(directory)
        code = """
import os, sys
sys.path.insert(0, sys.argv[1])
os.chdir(sys.argv[1])
import zscore_dashboard
assert zscore_dashboard.__file__.startswith(sys.argv[1])
from zscore_dashboard.serving.app import create_app
from zscore_dashboard.settings import load_settings
assert load_settings().indicators.ma_period == 200
assert create_app().test_client().get('/').status_code == 200
print('Packaged application and resources OK')
"""
        subprocess.run([sys.executable, "-I", "-c", code, directory], check=True)


if __name__ == "__main__":
    main()
