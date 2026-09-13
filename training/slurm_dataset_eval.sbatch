#!/bin/bash
# ==============================================================================
# AI Cortex Real Dataset Evaluation Job
# Targets Node 01 & Node 02 (12 Cores, 24GB RAM total) on Slurm HPC Cluster
# Partition: long-serial (Max Timelimit: 7 Days / 168 Hours)
# Shards and evaluates the 8,852 multi-domain training dataset samples in parallel
# ==============================================================================
#SBATCH --job-name=ai-cortex-dataset-eval
#SBATCH --partition=long-serial
#SBATCH --nodelist=node-01,node-02
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --time=7-00:00:00
#SBATCH --output=/work/ai-cortex/logs/job_eval_%j.out
#SBATCH --error=/work/ai-cortex/logs/job_eval_%j.err

echo "=================================================================="
echo " Starting AI Cortex Real Dataset Evaluation on Nodes 01 & 02"
echo " Host Controller: $(hostname) | Date: $(date)"
echo " Job ID: $SLURM_JOB_ID | Partition: $SLURM_JOB_PARTITION"
echo " Node List: $SLURM_JOB_NODELIST | Total Nodes: $SLURM_JOB_NUM_NODES"
echo " Target: Real Dataset Quality, Entropy, Diversity & ROUGE Evaluation"
echo " Output Log: /work/ai-cortex/logs/job_eval_${SLURM_JOB_ID}.out"
echo "=================================================================="

# Ensure directories exist
mkdir -p /work/ai-cortex/logs /work/ai-cortex/eval_results /work/ai-cortex/data

# Launch distributed evaluation worker across node-01 and node-02
srun python3 /work/ai-cortex/slurm_dataset_eval_worker.py

echo "=================================================================="
echo " AI Cortex Dataset Evaluation Completed on $(date)"
echo "=================================================================="
