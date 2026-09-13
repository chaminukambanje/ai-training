#!/usr/bin/env python3
"""
Slurm Cluster Dispatcher for AI Cortex.
Connects AI Cortex on ai-cortex-01 to the dedicated 4-node Slurm HPC Cluster
hosted on VMware ESXi (Controller: login-01 at 192.168.0.131, Compute Nodes: node-[01-04]).
Allows dispatching distributed training, data synthesis, and batch compute workloads.
"""

import os
import sys
import subprocess
import time
import argparse
from typing import Dict, Any, Optional

SLURM_LOGIN_NODE = os.environ.get("SLURM_LOGIN_NODE", "192.168.0.131")
SLURM_USER = os.environ.get("SLURM_USER", "root")

def run_remote_slurm(cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Executes a Slurm command on the login-01 controller via passwordless SSH."""
    ssh_cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
        f"{SLURM_USER}@{SLURM_LOGIN_NODE}", cmd
    ]
    return subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)

def get_cluster_status() -> Dict[str, Any]:
    """Retrieves live sinfo partition and node states from the ESXi Slurm cluster."""
    res = run_remote_slurm("sinfo -o '%P|%a|%l|%D|%T|%N'")
    if res.returncode != 0:
        return {"error": res.stderr.strip(), "online": False}
    
    partitions = []
    for line in res.stdout.strip().split("\n"):
        if "|" in line and not line.startswith("PARTITION"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                partitions.append({
                    "partition": parts[0].replace("*", ""),
                    "is_default": "*" in parts[0],
                    "available": parts[1],
                    "timelimit": parts[2],
                    "nodes": parts[3],
                    "state": parts[4],
                    "nodelist": parts[5]
                })
    return {"online": True, "controller": SLURM_LOGIN_NODE, "partitions": partitions}

def get_queue() -> Dict[str, Any]:
    """Retrieves active jobs in squeue."""
    res = run_remote_slurm("squeue -o '%i|%u|%P|%j|%T|%M|%l|%D|%R'")
    if res.returncode != 0:
        return {"error": res.stderr.strip(), "jobs": []}
    
    jobs = []
    for line in res.stdout.strip().split("\n"):
        if "|" in line and not line.startswith("JOBID"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 9:
                jobs.append({
                    "job_id": parts[0],
                    "user": parts[1],
                    "partition": parts[2],
                    "name": parts[3],
                    "state": parts[4],
                    "time": parts[5],
                    "timelimit": parts[6],
                    "nodes": parts[7],
                    "reason": parts[8]
                })
    return {"jobs": jobs, "count": len(jobs)}

def submit_job(script_content: str, job_name: str = "ai-cortex-job", partition: str = "standard", 
               nodes: int = 1, cpus: int = 4, memory: str = "6G", time_limit: str = "02:00:00") -> Dict[str, Any]:
    """Generates an sbatch script and submits it to the ESXi Slurm cluster."""
    full_sbatch = f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --partition={partition}
#SBATCH --nodes={nodes}
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={memory}
#SBATCH --time={time_limit}
#SBATCH --output=/tmp/{job_name}_%j.out
#SBATCH --error=/tmp/{job_name}_%j.err

echo "=== AI Cortex Slurm Batch Job Started ==="
echo "Node: $(hostname)"
echo "Job ID: $SLURM_JOB_ID"
echo "Allocated Cores: $SLURM_CPUS_PER_TASK"
date

{script_content}

echo "=== AI Cortex Job Finished Successfully ==="
date
"""
    # Write to temp on remote and submit
    remote_script = f"/tmp/slurm_sub_{int(time.time())}.sbatch"
    write_cmd = f"cat << 'EOF' > {remote_script}\n{full_sbatch}\nEOF\nchmod +x {remote_script} && sbatch {remote_script}"
    
    res = run_remote_slurm(write_cmd)
    if res.returncode == 0:
        out = res.stdout.strip()
        job_id = None
        import re
        m = re.search(r"Submitted batch job (\d+)", out)
        if m:
            job_id = m.group(1)
        return {"success": True, "job_id": job_id, "output": out, "script": remote_script}
    else:
        return {"success": False, "error": res.stderr.strip()}

def main():
    parser = argparse.ArgumentParser(description="AI Cortex ESXi Slurm Cluster Manager")
    subparsers = parser.add_subparsers(dest="subcommand")
    
    subparsers.add_parser("status", help="View cluster node and partition status")
    subparsers.add_parser("queue", help="View running and pending jobs")
    
    submit_p = subparsers.add_parser("submit", help="Submit a job to the cluster")
    submit_p.add_argument("--name", default="ai-cortex-task", help="Job name")
    submit_p.add_argument("--partition", default="standard", help="Slurm partition (standard, high-mem, debug)")
    submit_p.add_argument("--nodes", type=int, default=1, help="Number of nodes")
    submit_p.add_argument("--cpus", type=int, default=4, help="CPUs per task")
    submit_p.add_argument("--mem", default="6G", help="Memory allocation")
    submit_p.add_argument("--cmd", required=True, help="Shell command to execute in the batch job")

    args = parser.parse_args()
    
    if args.subcommand == "status":
        status = get_cluster_status()
        if not status.get("online"):
            print(f"❌ Slurm cluster offline: {status.get('error')}")
            sys.exit(1)
        print(f"\n⚡ ESXi Slurm HPC Cluster (Controller: {status['controller']}) Status:")
        print(f"{'PARTITION':<15} {'STATE':<8} {'NODES':<6} {'TIMELIMIT':<12} {'NODELIST'}")
        print("-" * 65)
        for p in status["partitions"]:
            print(f"{p['partition']:<15} {p['state']:<8} {p['nodes']:<6} {p['timelimit']:<12} {p['nodelist']}")
            
    elif args.subcommand == "queue":
        q = get_queue()
        print(f"\n📋 Active Queue ({q['count']} jobs):")
        if q['count'] == 0:
            print("  (Queue is currently idle)")
        else:
            for j in q["jobs"]:
                print(f"  Job #{j['job_id']}: {j['name']} ({j['user']}) [{j['state']}] on {j['nodes']} nodes")
                
    elif args.subcommand == "submit":
        print(f"🚀 Submitting '{args.name}' to ESXi Slurm cluster ({args.partition})...")
        res = submit_job(args.cmd, job_name=args.name, partition=args.partition, 
                         nodes=args.nodes, cpus=args.cpus, memory=args.mem)
        if res["success"]:
            print(f"✅ Successfully submitted Job ID #{res['job_id']}")
            print(f"   Response: {res['output']}")
        else:
            print(f"❌ Submission failed: {res.get('error')}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
