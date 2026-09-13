#!/usr/bin/env python3
"""
AI Cortex Multi-Task Slurm Cluster Manager.
Orchestrates split workloads across the 4-node Slurm cluster:
  - Nodes 01 & 02: Real Dataset Evaluation (Quality, Diversity, Entropy, ROUGE alignment)
  - Nodes 03 & 04: Sustained Compute & Neural Loss Optimization (~80% CPU Load)
"""

import os
import sys
import glob
import time
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any

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

def get_live_cluster_jobs() -> List[Dict[str, Any]]:
    """Fetches active jobs from squeue."""
    q_res = run_slurm("squeue -o '%i|%j|%P|%T|%M|%N'")
    jobs = []
    if q_res.returncode == 0 and q_res.stdout.strip():
        lines = [l.strip() for l in q_res.stdout.strip().split("\n") if "|" in l and not l.startswith("JOBID")]
        for l in lines:
            parts = l.split("|")
            if len(parts) >= 6:
                jobs.append({
                    "job_id": parts[0],
                    "name": parts[1],
                    "partition": parts[2],
                    "state": parts[3],
                    "elapsed": parts[4],
                    "nodes": parts[5]
                })
    return jobs

def get_checkpoints_from_dir(pattern: str) -> List[Dict[str, Any]]:
    res = run_slurm(f"cat {pattern} 2>/dev/null")
    checkpoints = []
    if res.returncode == 0 and res.stdout.strip():
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
    return checkpoints

def deploy_scripts_to_nfs() -> bool:
    """Synchronizes worker and sbatch scripts to shared /work/ai-cortex."""
    base_dir = Path("/opt/ai-cortex/training")
    if not base_dir.exists():
        base_dir = Path(__file__).parent

    files_to_sync = [
        "slurm_sustained_worker.py",
        "slurm_dataset_eval_worker.py",
        "slurm_sustained_compute.sbatch",
        "slurm_dataset_eval.sbatch"
    ]

    for fname in files_to_sync:
        fpath = base_dir / fname
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            deploy_cmd = f"""
cat << 'EOF' > /work/ai-cortex/{fname}
{content}
EOF
chmod +x /work/ai-cortex/{fname}
"""
            res = run_slurm(deploy_cmd)
            if res.returncode != 0:
                print(f"❌ Failed deploying {fname}: {res.stderr}")
                return False
    return True

def start_split_workloads():
    """Cancels any legacy job and launches both split workloads."""
    print("🚀 Initiating Split Cluster Workloads across Slurm Cluster...")
    print("   • Nodes 01 & 02: Real Dataset Evaluation (8,852 Multi-Domain Samples)")
    print("   • Nodes 03 & 04: Sustained 80% Compute & Matrix Optimization")

    # 1. Sync files to NFS
    if not deploy_scripts_to_nfs():
        print("❌ Script deployment failed.")
        return False

    # 2. Cancel legacy unified jobs if present
    run_slurm("scancel -n ai-cortex-80pct-sustained 2>/dev/null || true")

    # 3. Check active jobs
    jobs = get_live_cluster_jobs()
    job_names = [j["name"] for j in jobs]

    # 4. Dispatch Dataset Evaluation to Nodes 01 & 02
    if "ai-cortex-dataset-eval" not in job_names:
        res1 = run_slurm("sbatch /work/ai-cortex/slurm_dataset_eval.sbatch")
        if res1.returncode == 0:
            print(f"✅ Dispatched Dataset Evaluation Job to node-01,node-02: {res1.stdout.strip()}")
        else:
            print(f"❌ Failed dispatching Dataset Evaluation: {res1.stderr.strip()}")
    else:
        print("ℹ️  Dataset Evaluation job already active.")

    # 5. Dispatch Sustained Compute to Nodes 03 & 04
    if "ai-cortex-sustained-compute" not in job_names:
        res2 = run_slurm("sbatch /work/ai-cortex/slurm_sustained_compute.sbatch")
        if res2.returncode == 0:
            print(f"✅ Dispatched Sustained Compute Job to node-03,node-04: {res2.stdout.strip()}")
        else:
            print(f"❌ Failed dispatching Sustained Compute: {res2.stderr.strip()}")
    else:
        print("ℹ️  Sustained Compute job already active.")

    return True

def stop_all_workloads():
    """Cancels all AI Cortex jobs on the Slurm cluster."""
    print("🛑 Cancelling all active AI Cortex jobs...")
    res = run_slurm("scancel -n ai-cortex-dataset-eval,ai-cortex-sustained-compute,ai-cortex-80pct-sustained && echo 'Jobs cancelled'")
    print(res.stdout.strip() or res.stderr.strip())

def show_status():
    """Displays rich split cluster telemetry for both workloads."""
    jobs = get_live_cluster_jobs()
    compute_cps = get_checkpoints_from_dir("/work/ai-cortex/checkpoints/checkpoint_node-*.json")
    eval_cps = get_checkpoints_from_dir("/work/ai-cortex/eval_results/eval_report_node-*.json")

    print("\n" + "=" * 78)
    print(" ⚡ AI CORTEX MULTI-TASK SLURM CLUSTER TELEMETRY")
    print("=" * 78)

    print("\n[ACTIVE SLURM JOBS]")
    if not jobs:
        print("  No active AI Cortex jobs currently queued or running.")
    else:
        for j in jobs:
            print(f"  • Job #{j['job_id']} [{j['name']}] | State: {j['state']} | Nodes: {j['nodes']} | Elapsed: {j['elapsed']}")

    # Section 1: Real Dataset Evaluation Telemetry
    print("\n" + "-" * 78)
    print(" 📊 TASK A: REAL DATASET EVALUATION (Node-01, Node-02)")
    print("   Dataset: 8,852 ChatML Samples (20+ Ingested Domains)")
    print("-" * 78)
    if not eval_cps:
        print("  (Awaiting first evaluation reports in /work/ai-cortex/eval_results...)")
    else:
        print(f" {'NODE':<9} {'CORES':<7} {'THREADS':<9} {'1m LOAD':<9} {'CPU %':<7} {'EVALUATED':<12} {'ENTROPY':<9} {'TTR':<7} {'PASSES'}")
        print(" " + "-" * 76)
        for cp in eval_cps:
            node = cp.get("node", "unknown")
            cores = cp.get("total_cores", 0)
            threads = cp.get("active_threads", 0)
            sys_m = cp.get("system_metrics", {})
            load1 = sys_m.get("load_1m", 0.0)
            cpu_pct = sys_m.get("cpu_utilization_pct", 0.0)
            ev = cp.get("evaluation_progress", {})
            evaluated = f"{ev.get('samples_evaluated', 0):,}"
            passes = f"{ev.get('passes_completed', 0.0)}x"
            qm = cp.get("quality_metrics", {})
            entropy = qm.get("shannon_entropy", 0.0)
            ttr = qm.get("type_token_ratio", 0.0)
            print(f" {node:<9} {cores:<7} {threads:<9} {load1:<9} {cpu_pct:<7}% {evaluated:<12} {entropy:<9} {ttr:<7} {passes}")

        # Show live model alignment if available
        for cp in eval_cps:
            align = cp.get("model_alignment", {})
            if align.get("mean_rouge_l") is not None:
                print(f"\n  🎯 Live Model Alignment ({cp.get('node')} -> ai-cortex:latest):")
                print(f"     • Samples Tested: {align.get('samples_tested')}")
                print(f"     • Mean ROUGE-L Alignment Score: {align.get('mean_rouge_l')}")
                for s in align.get("recent_samples", [])[-1:]:
                    print(f"     • Latest Eval: '{s.get('prompt')}' -> ROUGE-L={s.get('rouge_l')} ({s.get('tokens_per_sec')} tok/s)")

    # Section 2: Sustained Compute Telemetry
    print("\n" + "-" * 78)
    print(" 🔥 TASK B: 80% SUSTAINED COMPUTE & MATRIX OPTIMIZATION (Node-03, Node-04)")
    print("   Workload: Dense Floating-Point Projections & Continuous Loss Simulation")
    print("-" * 78)
    if not compute_cps:
        print("  (Awaiting compute worker heartbeats in /work/ai-cortex/checkpoints...)")
    else:
        print(f" {'NODE':<9} {'CORES':<7} {'THREADS':<9} {'1m LOAD':<9} {'CPU %':<7} {'RAM USED':<14} {'TOKENS/MATH OPS'}")
        print(" " + "-" * 76)
        for cp in compute_cps:
            node = cp.get("node", "unknown")
            cores = cp.get("total_cores", 0)
            threads = cp.get("active_threads", 0)
            sys_m = cp.get("system_metrics", {})
            load1 = sys_m.get("load_1m", 0.0)
            cpu_pct = cp.get("cpu_utilization_pct", 0.0)
            ram = f"{sys_m.get('mem_used_mb', 0)}M/{sys_m.get('mem_total_mb', 0)}M"
            tokens = f"{cp.get('tokens_processed', 0):,}"
            print(f" {node:<9} {cores:<7} {threads:<9} {load1:<9} {cpu_pct:<7}% {ram:<14} {tokens}")

    print("\n" + "=" * 78 + "\n")

def main():
    parser = argparse.ArgumentParser(description="AI Cortex Multi-Task Slurm Cluster Manager")
    parser.add_argument("action", choices=["start", "stop", "status", "restart"], help="Action to perform")
    args = parser.parse_args()

    if args.action == "start":
        start_split_workloads()
        time.sleep(3)
        show_status()
    elif args.action == "stop":
        stop_all_workloads()
    elif args.action == "restart":
        stop_all_workloads()
        time.sleep(3)
        start_split_workloads()
        time.sleep(3)
        show_status()
    elif args.action == "status":
        show_status()

if __name__ == "__main__":
    main()
