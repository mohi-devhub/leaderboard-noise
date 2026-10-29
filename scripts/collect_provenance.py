"""Copy byte-identical launch/runtime sources, preserving different attestation levels."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

A10 = Path("results/study-20261028T065939Z")
INITIAL = Path("results/l4-followup-20261028T190732Z")
L4 = Path("results/l4-continuation-20261028T224638Z")


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(root):
    out = root / "provenance"
    out.mkdir(exist_ok=True)
    candidates = {}
    for base in ("scripts", "results"):
        for p in (root / base).rglob("*.py"):
            candidates.setdefault(digest(p), []).append(p)
    records = []

    def copy_hash(expected, destination, recorded_in, attestation):
        if expected not in candidates:
            raise RuntimeError("No saved source matches recorded digest: " + expected)
        src = candidates[expected][0]
        target = out / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        assert digest(target) == expected
        records.append(
            {
                "path": str(target.relative_to(root)),
                "sha256": expected,
                "saved_source": str(src.relative_to(root)),
                "recorded_in": recorded_in,
                "attestation": attestation,
            }
        )

    launch = read(root / A10 / "launch-source-sha256.json")
    for name in ("gpu_worker.py", "run_study.py"):
        copy_hash(
            launch["scripts/" + name],
            "a10/" + ("worker-pre-bos.py" if name == "gpu_worker.py" else name),
            str(A10 / "launch-source-sha256.json"),
            "launch-recorded source digest; early workers have no runtime self-hash",
        )
    fix = read(root / A10 / "tokenization-fix-archive.json")
    copy_hash(
        fix["runtime-fixes/tokenization/after.py"],
        "a10/worker-bos-fixed.py",
        str(A10 / "tokenization-fix-archive.json"),
        "runtime worker self-hash on later A10 models; correction installed before Llama",
    )
    launch_remaining = read(root / A10 / "remaining-launch-source-sha256.json")
    copy_hash(
        launch_remaining["scripts/study_model_job.py"],
        "a10/study_model_job.py",
        str(A10 / "remaining-launch-source-sha256.json"),
        "launch-recorded source digest",
    )
    functions = read(root / A10 / "submitted-function-source.json")
    for name, expected in functions["function_ast_sha256"].items():
        copy_hash(
            expected,
            "a10/" + name + ".py",
            str(A10 / "submitted-function-source.json"),
            "captured normalized function source; recorded digest matches snapshot bytes",
        )
    for session, folder, names in [
        (INITIAL, "l4-initial", ("gpu_worker.py", "study_model_job.py", "run_l4_followup.py")),
        (
            L4,
            "l4-continuation",
            ("gpu_worker.py", "study_model_job.py", "run_l4_followup.py", "followup_state.py"),
        ),
    ]:
        hashes = read(root / session / "source-hashes.json")
        for name in names:
            copy_hash(
                hashes["scripts/" + name],
                folder + "/" + name,
                str(session / "source-hashes.json"),
                "launch-recorded source digest; inference worker digest also recorded at runtime",
            )
    mapping = []
    for session in (A10, L4):
        summary = read(root / session / "summary.json")
        for name in summary["models"]:
            job = read(root / session / (name.rsplit("/", 1)[-1] + ".json"))
            for index, arm in enumerate(job["arms"]):
                observed = arm["metadata"].get("worker_source_sha256")
                expected = observed or launch["scripts/gpu_worker.py"]
                matches = [r["path"] for r in records if r["sha256"] == expected]
                if not matches:
                    raise RuntimeError("Runtime worker has no shipped matching source")
                mapping.append(
                    {
                        "session": str(session),
                        "model": name,
                        "process_index": index,
                        "arm": arm["metadata"]["arm"],
                        "worker_source_sha256": expected,
                        "attestation": "runtime_self_hash"
                        if observed
                        else "launch_only_no_runtime_self_hash",
                        "matching_shipped_source": matches[0],
                    }
                )
    manifest = {
        "files": records,
        "process_mapping": mapping,
        "note": "Source snapshots are not independent full-environment attestations. Early A10 processes lack runtime worker hashes.",
        "new_inference": False,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "SHA256SUMS").write_text(
        "".join(
            r["sha256"] + "  " + str(Path(r["path"]).relative_to("provenance")) + "\n"
            for r in records
        )
    )
    (out / "README.md").write_text(
        "# Executed-source provenance\n\nFiles are copied byte for byte from saved sources whose hashes match recorded launch or runtime evidence. `manifest.json` maps each retained process to its matching worker. Early A10 processes are launch-attested only; later A10 and L4 worker self-hashes are checked. Normalized serialized A10 function snapshots are shipped alongside full launcher/worker sources. The Llama BOS correction has separate before/after files.\n\nDo not format or modify these snapshots. They preserve executed/submitted code, including historical style and dependencies. Check `SHA256SUMS`; read each attestation label before claiming runtime coverage. These hashes are not third-party signatures.\n"
    )
    print(
        f"Copied {len(records)} source snapshots; mapped {len(mapping)} retained model/arm processes."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    collect(p.parse_args().root)
