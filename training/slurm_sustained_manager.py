#!/usr/bin/env python3
"""
AI Cortex 80% Sustained Cluster Manager.
Orchestrates continuous ~80% compute utilization across the 4-node Slurm cluster
(node-[01-04]) for extended periods of days and weeks.
"""

import os
import sys
import glob
import time
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any

SLURM_LOGIN_NODE = os.environ.get("SLURM_LOGIN_NODE", "192.168.0.131")
AI_CORTEX_HOST = "192.168.0.235"
SHARED_WORK_DIR = Path("/work/ai-cortex")

def run_ssh(host: str, cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    ssh_cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
        f"root@{host}", cmd
    ]
    return subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)

def run_slurm(cmd: str) -> subprocess.CompletedProcess:
    import socket
    if socket.gethostname() == "ai-cortex-01" or os.path.exists("/opt/ai-cortex"):
        return run_ssh(SLURM_LOGIN_NODE, cmd)
    else:
        nested = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@{SLURM_LOGIN_NODE} {json.dumps(cmd)}"
        return run_ssh(AI_CORTEX_HOST, nested)

def get_live_cluster_telemetry() -> Dict[str, Any]:
    """Inspects active checkpoints and sinfo to compute current cluster utilization."""
    res = run_slurm("cat /work/ai-cortex/checkpoints/checkpoint_*.json 2>/dev/null")
    checkpoints = []
    if res.returncode == 0 and res.stdout.strip():
        # Might contain multiple JSON blocks concatenated
        raw = res.stdout.strip()
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(raw):
            raw_slice = raw[idx:].strip()
            if not raw_slice:
                break
            try:
                obj, end_idx = decoder.raw_decode(raw_slice)
                checkpoints.append(obj)
                idx += end_idx
            except Exception:
                break

    # Get squeue state
    q_res = run_slurm("squeue -n ai-cortex-80pct-sustained -o '%i|%P|%T|%M|%N'")
    job_info = None
    if q_res.returncode == 0 and len(q_res.stdout.strip().split("\n")) > 1:
        lines = [l.strip() for l in q_res.stdout.strip().split("\n") if "|" in l and not l.startswith("JOBID")]
        if lines:
            parts = lines[0].split("|")
            job_info = {
                "job_id": parts[0],
                "partition": parts[1],
                "state": parts[2],
                "elapsed": parts[3],
                "nodes": parts[4]
            }

    return {
        "job": job_info,
        "nodes_active": len(checkpoints),
        "checkpoints": checkpoints
    }

def start_sustained_training():
    """Deploys worker code to shared /work and submits 7-day Slurm batch job."""
    print("🚀 Initiating 80% sustained training across all 4 Slurm nodes (node-[01-04])...")
    
    # 1. Ensure /work/ai-cortex is populated with worker script
    worker_src = Path("/opt/ai-cortex/training/slurm_sustained_worker.py")
    if not worker_src.exists():
        worker_src = Path(__file__).parent / "slurm_sustained_worker.py"
    
    with open(worker_src, "r") as f:
        worker_code = f.read()

    prep_cmd = f"""
mkdir -p /work/ai-cortex/logs /work/ai-cortex/checkpoints
cat << 'EOF' > /work/ai-cortex/slurm_sustained_worker.py
{worker_code}
EOF
chmod +x /work/ai-cortex/slurm_sustained_worker.py
"""
    res = run_slurm(prep_cmd)
    if res.returncode != 0:
        print(f"❌ Failed to prepare /work/ai-cortex: {res.stderr}")
        return False

    # 2. Check if job already active
    telemetry = get_live_cluster_telemetry()
    if telemetry["job"]:
        print(f"⚠️  Job already active! (Job ID #{telemetry['job']['job_id']} [{telemetry['job']['state']}] on {telemetry['job']['nodes']})")
        return True

    # 3. Submit sbatch job
    sbatch_script = Path("/opt/ai-cortex/training/slurm_sustained_train.sbatch")
    if not sbatch_script.exists():
        sbatch_script = Path(__file__).parent / "slurm_sustained_train.sbatch"

    with open(sbatch_script, "r") as f:
        sbatch_content = f.read()

    sub_cmd = f"""
cat << 'EOF' > /tmp/sustained_train.sbatch
{sbatch_content}
EOF
sbatch /tmp/sustained_train.sbatch
"""
    sub_res = run_slurm(sub_cmd)
    if sub_res.returncode == 0:
        print(f"✅ Successfully dispatched 80% sustained batch job to Slurm cluster!")
        print(f"   {sub_res.stdout.strip()}")
        return True
    else:
        print(f"❌ Submission failed: {sub_res.stderr.strip()}")
        return False

def stop_sustained_training():
    """Cancels the sustained batch job."""
    print("🛑 Cancelling sustained 80% training job...")
    res = run_slurm("scancel -n ai-cortex-80pct-sustained && echo 'Cancelled'")
    print(res.stdout.strip() or res.stderr.strip())

def show_status():
    """Displays formatted cluster telemetry."""
    telemetry = get_live_cluster_telemetry()
    job = telemetry.get("job")
    
    print("\n" + "=" * 70)
    print(" ⚡ AI CORTEX SLURM CLUSTER 80% SUSTAINED UTILIZATION TELEMETRY")
    print("=" * 70)
    
    if job:
        print(f" Batch Job: #{job['job_id']} ({job['state']}) | Partition: {job['partition']} (7-day max)")
        print(f" Nodes Allocated: {job['nodes']} | Elapsed Time: {job['elapsed']}")
    else:
        print(" Batch Job: No active sustained batch job in queue.")

    print("\n Node Telemetry:")
    print(f" {'NODE':<10} {'CORES':<8} {'THREADS':<10} {'1m LOAD':<10} {'CPU %':<8} {'RAM USED':<12} {'TOKENS'}")
    print(" " + "-" * 68)

    checkpoints = telemetry.get("checkpoints", [])
    if not checkpoints:
        print("  (Waiting for worker heartbeats in /work/ai-cortex/checkpoints...)")
    else:
        for cp in checkpoints:
            node = cp.get("node", "unknown")
            cores = cp.get("total_cores", 0)
            threads = cp.get("active_threads", 0)
            sys_m = cp.get("system_metrics", {})
            load1 = sys_m.get("load_1m", 0.0)
            cpu_pct = cp.get("cpu_utilization_pct", 0.0)
            ram = f"{sys_m.get('mem_used_mb', 0)}M/{sys_m.get('mem_total_mb', 0)}M"
            tokens = f"{cp.get('tokens_processed', 0):,}"
            print(f" {node:<10} {cores:<8} {threads:<10} {load1:<10} {cpu_pct:<8}% {ram:<12} {tokens}")
    print("=" * 70 + "\n")

def main():
    parser = argparse.ArgumentParser(description="AI Cortex 80% Sustained Slurm Cluster Manager")
    parser.add_argument("action", choices=["start", "stop", "status", "restart"], help="Action to perform")
    args = parser.parse_args()

    if args.action == "start":
        start_sustained_training()
        time.sleep(2)
        show_status()
    elif args.action == "stop":
        stop_sustained_training()
    elif args.action == "restart":
        stop_sustained_training()
        time.sleep(3)
        start_sustained_training()
        time.sleep(2)
        show_status()
    elif args.action == "status":
        show_status()

if __name__ == "__main__":
    main()
