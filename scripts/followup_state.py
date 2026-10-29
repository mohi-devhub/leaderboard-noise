"""Persist an execution claim before generation so platform replay cannot repeat work."""

import json


def begin_once(root, claim):
    path = root / "execution-claim.json"
    if path.exists():
        previous = json.loads(path.read_text())
        if previous["session"] != claim["session"]:
            raise RuntimeError("execution claim belongs to another session")
        manifest = root / "manifest.json"
        if manifest.exists():
            return json.loads(manifest.read_text())
        progress = root / "progress.json"
        result = (
            json.loads(progress.read_text())
            if progress.exists()
            else {"models": [], "budget_checks": []}
        )
        return dict(
            result,
            status="preemption_restart_blocked",
            error="A prior execution claimed this volume. Preserve checkpoints and re-forecast unfinished models before another allocation.",
        )
    path.write_text(json.dumps(claim) + "\n")
    return None
