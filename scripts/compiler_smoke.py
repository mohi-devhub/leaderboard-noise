"""Fail in the CPU image build if Triton's host compiler prerequisites are missing."""

from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sysconfig
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    compiler = shutil.which("cc")
    if compiler is None:
        raise RuntimeError("C compiler is required for Triton's runtime driver helpers")
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "compiler-check.o"
        subprocess.run(
            [
                compiler,
                "-I" + sysconfig.get_paths()["include"],
                "-x",
                "c",
                "-c",
                "-o",
                str(output),
                "-",
            ],
            input="#include <Python.h>\nint main(void) { return 0; }\n",
            text=True,
            check=True,
        )
    version = subprocess.check_output([compiler, "--version"], text=True).splitlines()[0]
    if args.output:
        args.output.write_text(
            json.dumps(
                {"passed": True, "compiler": compiler, "version": version, "python_headers": True}
            )
            + "\n"
        )
    print(version)
    print("C compiler and Python headers preflight passed")


if __name__ == "__main__":
    main()
