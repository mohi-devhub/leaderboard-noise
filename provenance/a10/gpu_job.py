@app.function(image=image, gpu='A10', cpu=(2, 4), memory=(8192, 16384), volumes={'/artifacts': volume}, secrets=[secret], max_containers=1, retries=0, timeout=timeout, startup_timeout=1800, scaledown_window=2, serialized=True, include_source=False)
def gpu_job(payload):
    import json
    import hashlib
    import os
    import sys
    import threading
    from datetime import datetime, timezone
    from pathlib import Path
    root = Path('/artifacts')
    start = time.monotonic()
    started = datetime.now(timezone.utc).isoformat()
    (root / 'gpu-started.json').write_text(json.dumps({'started_at': started}))
    volume.commit()
    guard = threading.Timer(payload['timeout_seconds'], lambda: os._exit(124))
    guard.daemon = True
    guard.start()
    sys.path.insert(0, '/opt')
    from study_model_job import execute_model
    result = {'status': 'running', 'started_at': started, 'models': []}
    try:
        import torch
        import subprocess
        gpu = torch.cuda.get_device_name()
        if gpu not in {'NVIDIA A10', 'NVIDIA A10G'}:
            raise RuntimeError('allocated GPU is outside the authorized Modal A10 tier')
        uuid = subprocess.check_output(['nvidia-smi', '--query-gpu=uuid', '--format=csv,noheader'], text=True).strip()
        result.update(gpu=gpu, gpu_uuid=uuid, cloud=os.environ.get('MODAL_CLOUD_PROVIDER'), region=os.environ.get('MODAL_REGION'))
        for model, forecast_row in zip(payload['models'], payload['forecasts'], strict=True):
            total = payload['spent_before_usd'] + 0.15 + (time.monotonic() - start + 120) * payload['combined_hourly_usd'] / 3600
            if total + forecast_row['reservation_usd'] > 12:
                result.update(status='budget_stop', error='next model would cross $12')
                break
            print(f"REMOTE_BUDGET_GATE {model['id']} total_estimate={total:.6f} next={forecast_row['reservation_usd']:.6f}", flush=True)
            task = {'model': model, 'items': payload['items'], 'timing_item_ids': payload['timing_item_ids'], 'config': payload['config'], 'execution_limit_seconds': forecast_row['execution_limit_seconds'], 'expected_gpu_uuid': uuid}
            value = execute_model(task)
            name = model['id'].rsplit('/', 1)[-1] + '.json'
            data = json.dumps(value).encode()
            (root / name).write_bytes(data)
            record = {'model': model['id'], 'file': name, 'sha256': hashlib.sha256(data).hexdigest(), 'status': value['status'], 'remote_seconds': value['remote_seconds'], 'forecast_seconds': forecast_row['forecast_seconds']}
            result['models'].append(record)
            (root / 'progress.json').write_text(json.dumps(result))
            volume.commit()
            print('REMOTE_MODEL_COMPLETE ' + json.dumps(record), flush=True)
            if value['status'] != 'complete':
                result.update(status='failed', error=value.get('error', 'worker failed'))
                break
        else:
            result['status'] = 'complete'
    except Exception as exc:
        result.update(status='failed', error_type=type(exc).__name__, error=str(exc))
    finally:
        guard.cancel()
    result['remote_seconds'] = time.monotonic() - start
    (root / 'manifest.json').write_text(json.dumps(result))
    volume.commit()
    return result
