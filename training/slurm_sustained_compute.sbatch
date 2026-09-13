#!/bin/bash
# ==============================================================================
# AI Cortex 80% Sustained Compute & Matrix Optimization Job
# Targets Node 03 & Node 04 (10 Cores, 24GB RAM total) on Slurm HPC Cluster
# Partition: long-serial (Max Timelimit: 7 Days / 168 Hours)
# Maintains ~80% CPU Load across assigned nodes continuously for days
# ==============================================================================
#SBATCH --job-name=ai-cortex-sustained-compute
#SBATCH --partition=long-serial
#SBATCH --nodelist=node-03,node-04
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --time=7-00:00:00
#SBATCH --output=/work/ai-cortex/logs/job_compute_%j.out
#SBATCH --error=/work/ai-cortex/logs/job_compute_%j.err

echo "=================================================================="
echo " Starting AI Cortex 80% Sustained Compute on Nodes 03 & 04"
echo " Host Controller: $(hostname) | Date: $(date)"
echo " Job ID: $SLURM_JOB_ID | Partition: $SLURM_JOB_PARTITION"
echo " Node List: $SLURM_JOB_NODELIST | Total Nodes: $SLURM_JOB_NUM_NODES"
echo " Target: ~80% Sustained Matrix Optimization & Neural Simulation"
echo " Output Log: /work/ai-cortex/logs/job_compute_${SLURM_JOB_ID}.out"
echo "=================================================================="

# Ensure directories exist
mkdir -p /work/ai-cortex/logs /work/ai-cortex/checkpoints

# Launch sustained compute worker across node-03 and node-04
srun python3 /work/ai-cortex/slurm_sustained_worker.py

echo "=================================================================="
echo " AI Cortex Sustained Compute Completed on $(date)"
echo "=================================================================="
