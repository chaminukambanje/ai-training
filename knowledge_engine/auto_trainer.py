#!/usr/bin/env python3
"""
AI Cortex Autonomous Long-Running Documentation Learner & Trainer.
Performs unattended ingestion, indexing, instruction synthesis, and model training
across: Microsoft, Red Hat, Linux, Amazon Web Services, GitHub, VMware, and Ubuntu.
All operations execute non-interactively (default answer YES).
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime

# Add knowledge engine to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from harvester import harvest_all
from dataset_synthesizer import generate_training_data
from modelfile_updater import update_modelfile, compile_ollama_model
from knowledge_indexer import get_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AI-LEARNER] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/opt/ai-cortex/data/training_learner.log", mode="a")
    ]
)
logger = logging.getLogger("auto_trainer")

def run_training_cycle(run_number: int = 1):
    logger.info(f"==================================================")
    logger.info(f"Starting Unattended Learning Cycle #{run_number} at {datetime.now().isoformat()}")
    logger.info(f"Target Domains: Microsoft, Red Hat, Linux, AWS, GitHub, VMware, Ubuntu, JASMIN, ARCHER, BBC, ZBC, SABC, GOV.UK, GOV.ZW, GOV.ZA")
    logger.info(f"Mode: Unattended Non-Interactive (Default YES)")
    logger.info(f"==================================================")

    # 1. Harvest & Index Documentation
    try:
        logger.info("[Step 1/4] Harvesting and Indexing Documentation...")
        harvest_count = harvest_all()
        logger.info(f"[Step 1/4 Completed] Harvested {harvest_count} docs.")
    except Exception as e:
        logger.error(f"Error in Harvester: {e}")

    # 2. Synthesize Instruction-Tuning Dataset
    try:
        logger.info("[Step 2/4] Synthesizing Instruction-Tuning Q&A Pairs...")
        new_samples = generate_training_data()
        logger.info(f"[Step 2/4 Completed] Generated {new_samples} new verified instruction pairs.")
    except Exception as e:
        logger.error(f"Error in Dataset Synthesizer: {e}")

    # 3. Update Modelfile & Compile Ollama Model
    try:
        logger.info("[Step 3/4] Updating Modelfile with Ingested Technical Metrics...")
        update_modelfile()
        logger.info("[Step 4/4] Non-interactive Ollama Model Compilation...")
        success = compile_ollama_model()
        if success:
            logger.info("[Step 4/4 Completed] AI Cortex model successfully retrained and updated in Ollama!")
        else:
            logger.warning("[Step 4/4 Warning] Ollama update encountered an issue, check logs.")
    except Exception as e:
        logger.error(f"Error in Model Compilation: {e}")

    stats = get_stats()
    logger.info(f"Cycle #{run_number} Finished! Current Knowledge Stats: {stats}")
    logger.info("==================================================")

def main():
    parser = argparse.ArgumentParser(description="AI Cortex Unattended Documentation Trainer")
    parser.add_argument("--once", action="store_true", help="Run a single training cycle and exit")
    parser.add_argument("--interval", type=int, default=3600, help="Interval between training cycles in seconds (default: 3600 = 1 hour)")
    args = parser.parse_args()

    cycle = 1
    if args.once:
        run_training_cycle(cycle)
        sys.exit(0)

    logger.info(f"Starting Continuous Long-Running Training Daemon (Interval: {args.interval}s)...")
    while True:
        run_training_cycle(cycle)
        cycle += 1
        logger.info(f"Sleeping for {args.interval} seconds until next unattended training cycle...")
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
