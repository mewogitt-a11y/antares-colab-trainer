#!/usr/bin/env python3
\"\"\"Dispatch a compute task to GitHub Actions and poll for results.\"\"\"
import urllib.request, urllib.error, json, base64, sys, time, os, subprocess

def get_token():
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
        "[Environment]::GetEnvironmentVariable('GITHUB_TOKEN','User')"],
        capture_output=True, text=True)
    return r.stdout.strip()

TOKEN = get_token()
REPO = "mewogitt-a11y/antares-colab-trainer"

def api(method, path, data=None):
    url = f"https://api.github.com{path}"
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
               "User-Agent": "SYSUS/1.0"}
    if data:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    else:
        body = None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read()) if resp.read() else {}

def dispatch(script_path, task_id="task-001"):
    with open(script_path, "rb") as f:
        script_b64 = base64.b64encode(f.read()).decode()
    
    api("POST", f"/repos/{REPO}/actions/workflows/compute_worker.yml/dispatches", {
        "ref": "main",
        "inputs": {"task_script": script_b64, "task_id": task_id}
    })
    print(f"Dispatched task {task_id} ({len(script_b64)} bytes encoded)")

def poll_runs(task_id, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        runs = api("GET", f"/repos/{REPO}/actions/runs?per_page=5")
        for run in runs.get("workflow_runs", []):
            if run["status"] == "completed":
                print(f"Run {run['id']}: {run['conclusion']} in {run['run_started_at']}")
                return run
            elif run["status"] in ("queued", "in_progress"):
                print(f"Run {run['id']}: {run['status']}...")
        time.sleep(15)
    print("Timeout waiting for run")
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: dispatch_task.py <script.py> [task-id]")
        sys.exit(1)
    task_id = sys.argv[2] if len(sys.argv) > 2 else f"task-{int(time.time())}"
    dispatch(sys.argv[1], task_id)
    print("Polling for completion...")
    poll_runs(task_id)
