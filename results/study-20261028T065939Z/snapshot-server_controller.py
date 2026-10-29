@app.function(image=image, cpu=(0.125, 0.25), memory=512, volumes={'/artifacts': volume}, max_containers=1, retries=0, timeout=timeout + 1900, serialized=True, include_source=False)
def server_controller(payload):
    import json
    from pathlib import Path
    submitted = time.monotonic()
    call = gpu_job.spawn(payload)
    (Path('/artifacts') / 'gpu-call.json').write_text(json.dumps({'call_id': call.object_id}))
    volume.commit()
    started = False
    while True:
        try:
            return call.get(timeout=15)
        except (modal.exception.FunctionTimeoutError, modal.exception.RemoteError):
            raise
        except TimeoutError:
            volume.reload()
            started = started or (Path('/artifacts') / 'gpu-started.json').exists()
            if not started and time.monotonic() - submitted >= 1800:
                call.cancel(terminate_containers=True)
                return {'status': 'allocation_timeout', 'models': [], 'error': 'no matching A10 allocation within 30 minutes'}
