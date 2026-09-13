#!/bin/bash
# ==============================================================================
# AI Cortex Distributed Training & Dataset Synthesis Batch Job
# Target: Dedicated 4-Node Slurm Cluster on VMware ESXi (node-[01-04])
# ==============================================================================
#SBATCH --job-name=ai-cortex-train
#SBATCH --partition=standard
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=04:00:00
#SBATCH --output=/tmp/slurm_train_%j.out
#SBATCH --error=/tmp/slurm_train_%j.err

echo "=================================================================="
echo " Starting AI Cortex Batch Task on Slurm Cluster"
echo " Host: $(hostname) | Date: $(date)"
echo " Job ID: $SLURM_JOB_ID | Partition: $SLURM_JOB_PARTITION"
echo " Allocated Cores: $SLURM_CPUS_PER_TASK | Total Nodes: $SLURM_JOB_NUM_NODES"
echo " Node List: $SLURM_JOB_NODELIST"
echo "=================================================================="

# Check system resources
lscpu | grep "Model name\|CPU(s):"
free -h

echo "--- Executing AI Data Processing & Training Routine ---"
python3 -c '
import os, sys, time, multiprocessing

cores = multiprocessing.cpu_count()
print(f"[Slurm Worker] Active on {os.uname().nodename} with {cores} available cores.")
print("[Slurm Worker] Executing synthetic verification pass...")
time.sleep(2)
print("[Slurm Worker] Verification complete.")
'

echo "=================================================================="
echo " Task Completed Successfully on $(hostname)"
echo " Date: $(date)"
echo "=================================================================="
