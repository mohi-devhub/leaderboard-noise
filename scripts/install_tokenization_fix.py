"""Apply the pre-Llama input-format correction to this study's active container once."""

import argparse
import base64
import json
from pathlib import Path
import subprocess

from run_pilot import command_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument("session", type=Path)
    args = p.parse_args()
    s = args.session
    handles = json.loads((s / "remaining-controller-handle.json").read_text())
    gpu_call = json.loads((s / "remaining-gpu-call.json").read_text())["call_id"]
    calls = command_json("function", "calls", handles["gpu_function_id"], "--json")
    call = next(c for c in calls if c["function_call_id"] == gpu_call)
    if call["status"] != "running":
        raise RuntimeError("GPU job is not running; refuse mutation")
    expected = json.loads((s / "remaining-launch-source-sha256.json").read_text())[
        "scripts/gpu_worker.py"
    ]
    new = Path("scripts/gpu_worker.py").read_bytes()
    encoded = base64.b64encode(new).decode()
    code = """import base64,hashlib,json
from pathlib import Path
from datetime import datetime,timezone
active=[]
for p in Path('/tmp').glob('tmp*/input.json'):
 try:
  d=json.loads(p.read_text())
  if 'model' in d:active.append(d['model']['id'])
 except (OSError,ValueError):pass
if 'meta-llama/Llama-3.2-3B-Instruct' in active:raise RuntimeError('Llama already started; refuse a mid-model input change')
p=Path('/opt/gpu_worker.py');old=p.read_bytes();new=base64.b64decode(ENCODED)
if old==new:
 print(json.dumps({'already_applied':True,'sha256':hashlib.sha256(new).hexdigest()}));raise SystemExit(0)
if hashlib.sha256(old).hexdigest()!=EXPECTED:raise RuntimeError('unexpected worker source; refuse overwrite')
compile(new,str(p),'exec')
root=Path('/artifacts/runtime-fixes/tokenization');root.mkdir(parents=True,exist_ok=True)
(root/'before.py').write_bytes(old);(root/'after.py').write_bytes(new)
tmp=p.with_suffix('.py.pending');tmp.write_bytes(new);tmp.replace(p)
receipt={'at':datetime.now(timezone.utc).isoformat(),'active_models':active,'old_sha256':hashlib.sha256(old).hexdigest(),'new_sha256':hashlib.sha256(new).hexdigest(),'change':'Llama rendered-chat tokenization add_special_tokens=False; other models keep defaults','llama_not_started':True}
(root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\\n')
print(json.dumps(receipt))
""".replace("EXPECTED", repr(expected)).replace("ENCODED", repr(encoded))
    result = subprocess.run(
        [".venv/bin/modal", "container", "exec", call["container_id"], "--", "python", "-c", code],
        capture_output=True,
        text=True,
    )
    (s / "tokenization-fix-install.log").write_text(result.stdout + result.stderr)
    print(result.stdout[-2000:])
    print(result.stderr[-1000:])
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
