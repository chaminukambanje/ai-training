#!/bin/bash
# ==============================================================================
# AI Cortex 80% Sustained Cluster Training Job
# Targets all 4 nodes (node-[01-04]) on VMware ESXi Slurm HPC Cluster
# Partition: long-serial (Max Timelimit: 7 Days / 168 Hours)
# Maintains ~80% CPU Load across 22 cores continuously for days
# ==============================================================================
#SBATCH --job-name=ai-cortex-80pct-sustained
#SBATCH --partition=long-serial
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=1
#SBATCH --time=7-00:00:00
#SBATCH --output=/work/ai-cortex/logs/job_%j.out
#SBATCH --error=/work/ai-cortex/logs/job_%j.err

echo "=================================================================="
echo " Starting AI Cortex 80% Sustained Multi-Day Batch Run"
echo " Host Controller: $(hostname) | Date: $(date)"
echo " Job ID: $SLURM_JOB_ID | Partition: $SLURM_JOB_PARTITION"
echo " Node List: $SLURM_JOB_NODELIST | Total Nodes: $SLURM_JOB_NUM_NODES"
echo " Target: ~80% Sustained Utilization Across All 4 Compute Nodes"
echo " Output Log: /work/ai-cortex/logs/job_${SLURM_JOB_ID}.out"
echo "=================================================================="

# Ensure shared directories exist on NFS
mkdir -p /work/ai-cortex/logs /work/ai-cortex/checkpoints

# Sync worker script to shared /work/ai-cortex
cp -f /home/mbanjec/ai-cortex/training/slurm_sustained_worker.py /work/ai-cortex/slurm_sustained_worker.py 2>/dev/null || true
chmod +x /work/ai-cortex/slurm_sustained_worker.py

# Launch multi-node sustained worker across node-[01-04]
srun python3 /work/ai-cortex/slurm_sustained_worker.py

echo "=================================================================="
echo " AI Cortex 80% Sustained Run Completed on $(date)"
echo "=================================================================="
