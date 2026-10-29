"""Build the paper from saved artifacts using an explicitly pinned local TeX tool."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tectonic", default=shutil.which("tectonic"))
    parser.add_argument("--only-cached", action="store_true")
    args = parser.parse_args()
    if not args.tectonic:
        parser.error(
            "install the official digest-pinned engine in paper/toolchain.json, or pass --tectonic PATH"
        )
    version = subprocess.run(
        [args.tectonic, "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    toolchain = json.loads(Path("paper/toolchain.json").read_text())
    if toolchain["tectonic_version"] not in version:
        parser.error("this build requires the pinned Tectonic version in paper/toolchain.json")
    for script in ["scripts/paper_assets.py", "scripts/collect_provenance.py"]:
        subprocess.run([sys.executable, script], check=True)
    command = [args.tectonic, "--untrusted", "--keep-logs", "--bundle", toolchain["bundle_url"]]
    if args.only_cached:
        command.append("--only-cached")
    command.append("paper/main.tex")
    subprocess.run(command, check=True)
    print("PDF SHA256 " + hashlib.sha256(Path("paper/main.pdf").read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
