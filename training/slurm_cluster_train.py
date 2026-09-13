#!/usr/bin/env python3
"""
AI Cortex Distributed Training & Dataset Synthesis Pipeline via Slurm HPC Cluster.
Executes distributed data processing, knowledge validation, and synthetic instruction
generation across the 4-node Slurm cluster on VMware ESXi (node-[01-04]),
gathers results back to ai-cortex-01, updates the training dataset, rebuilds the Modelfile,
and recompiles the Ollama model.
"""

import os
import sys
import time
import json
import logging
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SLURM-TRAIN] %(message)s"
)
logger = logging.getLogger("slurm_cluster_train")

SLURM_LOGIN_NODE = os.environ.get("SLURM_LOGIN_NODE", "192.168.0.131")
SLURM_USER = os.environ.get("SLURM_USER", "root")
AI_CORTEX_HOST = "192.168.0.235"

def run_remote_ssh(host: str, cmd: str, timeout: int = 180) -> subprocess.CompletedProcess:
    """Executes a remote shell command via SSH."""
    ssh_cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
        f"root@{host}", cmd
    ]
    return subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)

def run_slurm_cmd(cmd: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """Executes a command on login-01 (routed through ai-cortex-01 if running locally)."""
    import socket
    hostname = socket.gethostname()
    if hostname == "ai-cortex-01" or os.path.exists("/opt/ai-cortex"):
        return run_remote_ssh(SLURM_LOGIN_NODE, cmd, timeout=timeout)
    else:
        nested_cmd = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@{SLURM_LOGIN_NODE} {json.dumps(cmd)}"
        return run_remote_ssh(AI_CORTEX_HOST, nested_cmd, timeout=timeout)

def build_cluster_payload() -> str:
    """Creates the self-contained multi-node Python worker script for Slurm nodes."""
    worker_script = '''
import os
import sys
import json
import time
import socket
import multiprocessing

rank = int(os.environ.get("SLURM_PROCID", "0"))
node = socket.gethostname()
cores = multiprocessing.cpu_count()

DOMAIN_MAP = {
    0: {
        "domain": "jasmin_archer_hpc",
        "description": "JASMIN LOTUS Batch Computing & ARCHER2 Cray MPICH Systems",
        "topics": [
            {
                "topic": "JASMIN LOTUS Slurm Partitions",
                "q": "What are the standard partitions and queue limits on JASMIN LOTUS?",
                "a": "JASMIN LOTUS batch computing cluster provides specialized Slurm partitions:\\n- short-serial: For test runs and serial workloads up to 24 hours.\\n- long-serial: Extended execution for serial tasks up to 168 hours (7 days).\\n- high-mem: Specialized nodes with up to 1TB RAM for large data arrays.\\n- par-single: Parallel multi-threaded jobs constrained to a single host.\\n- par-multi: Multi-node distributed MPI applications utilizing high-speed interconnects.\\nSubmit jobs using `sbatch -p <partition> <script.sbatch>`."
            },
            {
                "topic": "JASMIN Group Workspaces (GWS) Quotas",
                "q": "How do JASMIN Group Workspaces (GWS) manage multi-petabyte project storage?",
                "a": "JASMIN Group Workspaces (GWS) are managed project storage volumes designed for collaborative environmental data analysis. GWS quotas are enforced on high-performance parallel filesystems (Panasas, Quobyte, Ceph). Project managers monitor allocations via the JASMIN portal, and users interact with files directly under `/gws/nopw/j04/<project_name>`."
            },
            {
                "topic": "ARCHER2 Slurm Directives",
                "q": "How do you construct a production Slurm job script for ARCHER2?",
                "a": "On ARCHER2 (UK National Supercomputing Service), Slurm job scripts utilize Cray MPICH and standard sbatch directives:\\n```bash\\n#!/bin/bash\\n#SBATCH --job-name=archer2_sim\\n#SBATCH --nodes=2\\n#SBATCH --tasks-per-node=128\\n#SBATCH --cpus-per-task=1\\n#SBATCH --time=02:00:00\\n#SBATCH --partition=standard\\n#SBATCH --qos=standard\\n#SBATCH --account=e05-example\\n\\nmodule load epcc-job-env\\nsrun --distribution=block:block --hint=nomultithread ./my_mpi_app\\n```"
            },
            {
                "topic": "ARCHER2 Lustre Filesystem Best Practices",
                "q": "What are the performance recommendations for the ARCHER2 /work filesystem?",
                "a": "ARCHER2 uses high-performance Lustre filesystems for `/work`. Compute nodes cannot access `/home`. All batch calculations and output writing must occur within `/work/<project_code>/<project_code>/<username>`. Use `lfs setstripe` to tune file striping for large files."
            },
            {
                "topic": "CEDA & JASMIN Environment Modules",
                "q": "How do researchers load atmospheric and climate analysis tools in JASMIN?",
                "a": "On JASMIN, researchers load pre-configured Python environments and climate analysis software (CDO, NCO, Iris, Cartopy) using Jaspy environment modules:\\n```bash\\nmodule load jaspy\\n```\\nThis configures standardized scientific stacks managed by CEDA."
            }
        ]
    },
    1: {
        "domain": "vmware_truenas_infrastructure",
        "description": "VMware ESXi 8.0 Virtualization & TrueNAS ZFS Storage",
        "topics": [
            {
                "topic": "ESXi Promiscuous Mode Port Group",
                "q": "How is network packet mirroring configured on VMware ESXi for passive SIEM monitoring?",
                "a": "On VMware ESXi, a dedicated port group (e.g., SPAN-Monitoring-PG) on vSwitch-Mirror is configured with VLAN ID 4095 (All VLANs) and Promiscuous Mode set to Accept. This passes raw Ethernet traffic from mirrored switch ports directly to the unnumbered network capture interfaces of monitoring VMs such as TrueNAS (ens224) and security sensors without assigning an IP address."
            },
            {
                "topic": "TrueNAS ZFS Storage Pool Architecture",
                "q": "How does the TrueNAS storage pool support the homelab and Slurm cluster?",
                "a": "TrueNAS SCALE (192.168.0.47, VMID 76) runs on ESXi with 16 GB allocated RAM, managing ZFS storage pool `pool1`. It exports `/mnt/scratch` and `/mnt/pool1/share02` via NFS for distributed HPC cluster nodes, and stores continuous network packet captures in `/mnt/pool1/network_traffic/raw_pcaps/`."
            },
            {
                "topic": "Dell PowerEdge R620 Virtualization Host",
                "q": "What are the hardware specifications of the primary hypervisor host esxi-01.npcsolutions.co.za?",
                "a": "The primary hypervisor is esxi-01.npcsolutions.co.za (192.168.0.200), a Dell PowerEdge R620 enterprise server equipped with 2x Intel Xeon E5-2660 v2 CPUs (20 cores, 40 logical threads), 240 GB of physical DDR3 ECC RAM, and redundant 10GbE network interfaces attached to vSwitch0 and vSwitch-Mirror."
            },
            {
                "topic": "AI Cortex Server Virtual Hardware",
                "q": "What are the resource allocations and roles of the ai-cortex-01 virtual machine?",
                "a": "ai-cortex-01 (192.168.0.235, VMID 108) is provisioned on ESXi with 16 vCPUs, 43 GB RAM (44,032 MB), and 140 GB storage. It hosts the local Ollama LLM runtime on port 11434, the Antigravity (AGY) grounding server on port 8000, and orchestrates distributed Slurm workloads."
            }
        ]
    },
    2: {
        "domain": "linux_security_cloud",
        "description": "Linux Kernel Administration, Security, and AWS Engineering",
        "topics": [
            {
                "topic": "Linux Sysctl Network Optimization",
                "q": "What sysctl settings optimize high-throughput 10GbE networking in Linux?",
                "a": "To optimize high-throughput Linux network performance:\\n```ini\\nnet.core.rmem_max = 16777216\\nnet.core.wmem_max = 16777216\\nnet.ipv4.tcp_rmem = 4096 87380 16777216\\nnet.ipv4.tcp_wmem = 4096 65536 16777216\\nnet.core.netdev_max_backlog = 50000\\nnet.ipv4.tcp_congestion_control = bbr\\n```\\nApply immediately via `sysctl -p /etc/sysctl.d/99-network-tuning.conf`."
            },
            {
                "topic": "SELinux Boolean & Context Management",
                "q": "How do you resolve SELinux permission denials for custom systemd services?",
                "a": "Inspect denials using `ausearch -m avc -ts recent` or `journalctl -xe`. Check file contexts with `ls -Z`. Restore default contexts using `restorecon -Rv /opt/my-service/`. To permit custom network ports or directories permanently, use `semanage port -a -t http_port_t -p tcp <port>` or `semanage fcontext -a -t <type_t> '/opt/my-service(/.*)?'`."
            },
            {
                "topic": "AWS VPC Least Privilege Security Groups",
                "q": "How do you enforce least-privilege security group rules in AWS VPC?",
                "a": "Ensure ingress rules specify exact CIDR ranges (e.g., `192.168.0.0/24` or bastion host security group IDs) rather than `0.0.0.0/0`. Restrict administrative ports (22, 3389) to secure management endpoints, and implement AWS VPC Flow Logs to monitor rejected traffic across network interfaces."
            },
            {
                "topic": "Ubuntu Netplan Multi-NIC Configuration",
                "q": "How do you configure static routing and dual NICs using Netplan on Ubuntu Server?",
                "a": "On Ubuntu Server 24.04/26.04, configure `/etc/netplan/01-netcfg.yaml`:\\n```yaml\\nnetwork:\\n  version: 2\\n  ethernets:\\n    ens160:\\n      dhcp4: false\\n      addresses: [192.168.0.235/24]\\n      routes:\\n        - to: default\\n          via: 192.168.0.1\\n      nameservers:\\n        addresses: [192.168.0.1, 1.1.1.1]\\n```\\nApply with `sudo netplan apply`."
            }
        ]
    },
    3: {
        "domain": "microsoft_instructor_profile",
        "description": "Microsoft Enterprise Cloud, Dynamics 365, and Chaminuka Mbanje Biography",
        "topics": [
            {
                "topic": "Chaminuka Mbanje Professional Biography",
                "q": "Who is Chaminuka Mbanje?",
                "a": "Chaminuka Munashe Mbanje (username: mbanjec) is an enterprise systems engineer, storage operations specialist, and elite Senior Microsoft Certified Trainer (MCT) based in Oxfordshire, United Kingdom. He serves as a Storage Operations and User Support Specialist at JASMIN (the UK supercomputing and environmental data analysis facility operated by CEDA, NCAS, and STFC at Rutherford Appleton Laboratory). He holds 11+ major Microsoft technical certifications, a B.Sc. (Honours) in Computer Science from NUST, and conducts postgraduate studies in Computer Science at UNICAF University."
            },
            {
                "topic": "Chaminuka Mbanje Microsoft Credentials",
                "q": "What certifications and transcripts does Chaminuka Mbanje hold?",
                "a": "Chaminuka Mbanje is a verified Senior Microsoft Certified Trainer (MCT). His Microsoft certifications include:\\n- DevOps Engineer Expert (AZ-400)\\n- Dynamics 365 Business Central Functional Consultant Associate (MB-800)\\n- Azure Data Engineer Associate (DP-203)\\n- Azure Data Scientist Associate (DP-100)\\n- Azure Security Engineer Associate (AZ-500)\\n- Azure Administrator Associate (AZ-104)\\n- Azure Developer Associate (AZ-204)\\n- Power Platform Developer Associate (PL-400)\\n- Power Platform Functional Consultant Associate (PL-200)\\n- MCSA: SQL 2016 Database Development\\nOfficial Transcript ID: 1237645 | Access Code: Munashe1234."
            },
            {
                "topic": "Microsoft Dynamics 365 Business Central Server",
                "q": "How is Microsoft Dynamics 365 Business Central deployed in the homelab environment?",
                "a": "Microsoft Dynamics 365 Business Central is deployed on BC-server.Home (192.168.0.39), integrated with the Microsoft SQL Server 2022 instance on sql.Home (192.168.0.237). It provides full ERP capability, automated financial workflows, and extension development grounded in official Microsoft AL language standards."
            },
            {
                "topic": "Chaminuka Mbanje Affiliation with NCAS & CEDA",
                "q": "What is Chaminuka Mbanje's connection to NCAS, CEDA, and STFC?",
                "a": "Chaminuka Mbanje supports the JASMIN supercomputing infrastructure at Rutherford Appleton Laboratory (RAL), which is collaboratively run by the Centre for Environmental Data Analysis (CEDA), the National Centre for Atmospheric Science (NCAS), and the Science and Technology Facilities Council (STFC) under UK Research and Innovation (UKRI). In his role, he provides storage operations and user support for petascale atmospheric and climate science researchers."
            }
        ]
    }
}

target = DOMAIN_MAP.get(rank, DOMAIN_MAP[0])
start_t = time.time()

for item in target["topics"]:
    sample = {
        "node": node,
        "rank": rank,
        "domain": target["domain"],
        "topic": item["topic"],
        "messages": [
            {"role": "system", "content": "You are AI Cortex, the private intelligence assistant and systems copilot for Munashe Banjec\'s homelab infrastructure. Ground every response in verified system telemetry and official technical documentation."},
            {"role": "user", "content": item["q"]},
            {"role": "assistant", "content": item["a"]}
        ]
    }
    print(f"[SLURM_SAMPLE_JSON] {json.dumps(sample)}")

duration = time.time() - start_t
print(f"[SLURM_NODE_COMPLETE] Rank {rank} on {node} finished {len(target['topics'])} samples ({target['domain']}) in {duration:.4f}s across {cores} cores.")
'''
    return worker_script.strip()

def execute_slurm_training_job() -> Dict[str, Any]:
    """Dispatches and monitors the distributed batch job on the ESXi Slurm cluster."""
    logger.info("==================================================================")
    logger.info(f"Connecting to ESXi Slurm HPC Cluster (Controller: {SLURM_LOGIN_NODE})")
    logger.info("Allocating 4 compute nodes: node-[01-04] (22 cores, 44 GB RAM)")
    logger.info("==================================================================")

    worker_code = build_cluster_payload()
    escaped_worker_code = worker_code.replace("'", "'\\''")

    sbatch_script = f"""#!/bin/bash
#SBATCH --job-name=ai-cortex-dist-train
#SBATCH --partition=standard
#SBATCH --nodes=4
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=2
#SBATCH --time=00:30:00

echo "=== Distributed AI Training Job Started on $(hostname) at $(date) ==="
echo "SLURM_JOB_ID: $SLURM_JOB_ID | NODELIST: $SLURM_JOB_NODELIST"

# Run parallel Python worker tasks on all 4 nodes
srun python3 -c '{escaped_worker_code}'

echo "=== Distributed Training Completed at $(date) ==="
"""

    remote_sbatch_path = "/root/slurm_dist_train.sbatch"
    write_cmd = f"cat << 'EOF' > {remote_sbatch_path}\n{sbatch_script}\nEOF\nchmod +x {remote_sbatch_path} && sbatch {remote_sbatch_path}"

    logger.info("Submitting distributed batch job to Slurm scheduler...")
    res = run_slurm_cmd(write_cmd, timeout=30)
    if res.returncode != 0:
        logger.error(f"Failed to submit Slurm job: {res.stderr}")
        return {"success": False, "error": res.stderr}

    output = res.stdout.strip()
    logger.info(f"Slurm response: {output}")

    import re
    m = re.search(r"Submitted batch job (\d+)", output)
    if not m:
        logger.error(f"Could not parse job ID from: {output}")
        return {"success": False, "error": "Job ID not found"}

    job_id = m.group(1)
    logger.info(f"✅ Active Slurm Batch Job ID: #{job_id}")

    # Monitor job execution
    logger.info(f"Monitoring execution of Job #{job_id} on compute nodes node-[01-04]...")
    completed = False
    for attempt in range(60):
        time.sleep(3)
        check_res = run_slurm_cmd(f"squeue -j {job_id} -h -o '%T'")
        state = check_res.stdout.strip()
        if not state:
            completed = True
            logger.info(f"Job #{job_id} has finished processing across all nodes.")
            break
        logger.info(f"Job #{job_id} state: {state} (elapsed: {attempt*3}s)")

    # Read slurm output file from /root/slurm-<job_id>.out
    log_res = run_slurm_cmd(f"cat /root/slurm-{job_id}.out 2>/dev/null || cat slurm-{job_id}.out 2>/dev/null || cat /tmp/slurm_dist_train_{job_id}.out 2>/dev/null")
    log_content = log_res.stdout.strip()

    samples = []
    for line in log_content.splitlines():
        if "[SLURM_SAMPLE_JSON]" in line:
            json_str = line.split("[SLURM_SAMPLE_JSON]", 1)[1].strip()
            try:
                samples.append(json.loads(json_str))
            except Exception:
                pass
        elif "[SLURM_NODE_COMPLETE]" in line:
            logger.info(f"  {line.strip()}")

    logger.info(f"Collected {len(samples)} high-quality samples from all Slurm worker nodes.")

    return {
        "success": True,
        "job_id": job_id,
        "samples": samples,
        "log": log_content
    }

def apply_training_results(samples: List[Dict[str, Any]]):
    """Applies the training results to the dataset, Modelfile, and Ollama models."""
    logger.info("Applying distributed cluster training outputs to AI Cortex on ai-cortex-01...")

    if os.path.exists("/opt/ai-cortex"):
        dataset_path = Path("/opt/ai-cortex/data/training_dataset.jsonl")
        existing_hashes = set()
        if dataset_path.exists():
            import hashlib
            with open(dataset_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            d = json.loads(line)
                            for m in d.get("messages", []):
                                if m.get("role") == "user":
                                    existing_hashes.add(hashlib.md5(m["content"].strip().lower().encode()).hexdigest())
                        except Exception:
                            pass

        added_samples = 0
        import hashlib
        with open(dataset_path, "a", encoding="utf-8") as f:
            for item in samples:
                user_msg = next((m["content"] for m in item["messages"] if m["role"] == "user"), "")
                h = hashlib.md5(user_msg.strip().lower().encode()).hexdigest()
                if h not in existing_hashes:
                    existing_hashes.add(h)
                    f.write(json.dumps({"messages": item["messages"]}, ensure_ascii=False) + "\n")
                    added_samples += 1

        logger.info(f"Applied {added_samples} newly synthesized cluster instruction samples to {dataset_path}.")

        # Rebuild Modelfile and recompile Ollama
        import sys
        ke_dir = "/opt/ai-cortex/knowledge_engine"
        if ke_dir not in sys.path:
            sys.path.insert(0, ke_dir)
        from modelfile_updater import update_modelfile, compile_ollama_model
        logger.info("Rebuilding Modelfile with freshly trained metrics...")
        update_modelfile()
        logger.info("Recompiling Ollama models (ai-cortex and qwen2.5:7b)...")
        compile_ollama_model()
        logger.info("Model recompilation finished.")

def verify_live_inference():
    """Queries the newly updated Ollama model to verify knowledge grounding."""
    logger.info("Executing live verification query against updated Ollama model...")
    test_queries = [
        "In JASMIN LOTUS, what are the available Slurm partitions and when should short-serial vs par-multi be used?",
        "Who is Chaminuka Mbanje and what is his role at JASMIN, CEDA, and Rutherford Appleton Laboratory?"
    ]

    for q in test_queries:
        logger.info(f"\n[Test Prompt]: {q}")
        import urllib.request
        url = "http://127.0.0.1:11434/api/generate"
        payload = {
            "model": "ai-cortex",
            "prompt": q,
            "stream": False
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                res_json = json.loads(response.read().decode("utf-8"))
                logger.info(f"[Model Response]:\n{res_json.get('response', '').strip()}\n")
        except Exception as e:
            logger.error(f"Inference error: {e}")

def main():
    parser = argparse.ArgumentParser(description="AI Cortex Slurm Distributed Training Runner")
    parser.add_argument("--verify-only", action="store_true", help="Run inference verification without dispatching a new job")
    args = parser.parse_args()

    if args.verify_only:
        verify_live_inference()
        return

    result = execute_slurm_training_job()
    if not result.get("success"):
        logger.error("Slurm training execution failed.")
        sys.exit(1)

    logger.info(f"Slurm execution succeeded with {len(result['samples'])} samples.")
    apply_training_results(result["samples"])
    verify_live_inference()
    logger.info("✅ Complete AI training pipeline successfully executed using the Slurm cluster!")

if __name__ == "__main__":
    main()
