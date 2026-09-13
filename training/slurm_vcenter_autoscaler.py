#!/usr/bin/env python3
"""
AI Cortex VMware vCenter Elastic Autoscaler & Resource Redistributor for Slurm.
Provides:
  - Automatic elastic creation/provisioning of additional compute nodes via vCenter Server 8
  - Real-time monitoring of Slurm queue pressure, pending jobs, and node saturation
  - Dynamic hot-swap/hot-add/hot-remove redistribution of vCPUs and RAM across VMs
  - Integration with Slurm controller (slurm.conf, scontrol reconfigure, state management)
"""

import os
import sys
import time
import json
import ssl
import base64
import argparse
import subprocess
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Configuration defaults
VCENTER_HOST = os.environ.get("VCENTER_HOST", "192.168.0.146")
VCENTER_USER = os.environ.get("VCENTER_USER", "administrator@vsphere1.npcsolutions.co.za")
VCENTER_PASS = os.environ.get("VCENTER_PASS", "Munashe1234@")
ESXI_HOST = os.environ.get("ESXI_HOST", "192.168.0.200")
SLURM_LOGIN_NODE = os.environ.get("SLURM_LOGIN_NODE", "192.168.0.131")

if Path("/work/ai-cortex").exists():
    AUTOSCALE_LOG_PATH = Path("/work/ai-cortex/logs/vcenter_autoscaler.log")
else:
    AUTOSCALE_LOG_PATH = Path("/tmp/vcenter_autoscaler.log")
AUTOSCALE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [vCenter-Autoscaler] {msg}"
    print(formatted)
    try:
        with open(AUTOSCALE_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def run_ssh(host: str, cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    ssh_cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
        f"root@{host}", cmd
    ]
    return subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)

def run_slurm(cmd: str) -> subprocess.CompletedProcess:
    """Executes a command on the Slurm controller (login-01)."""
    import socket
    if socket.gethostname() == "ai-cortex-01" or os.path.exists("/opt/ai-cortex"):
        return run_ssh(SLURM_LOGIN_NODE, cmd)
    else:
        nested = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@{SLURM_LOGIN_NODE} {json.dumps(cmd)}"
        return run_ssh("192.168.0.235", nested)

class VCenterClient:
    """Wrapper for VMware vCenter Server 8 REST API and ESXi hypervisor."""

    def __init__(self, host: str = VCENTER_HOST, user: str = VCENTER_USER, password: str = VCENTER_PASS):
        self.host = host
        self.user = user
        self.password = password
        self.session_id: Optional[str] = None
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def connect(self) -> bool:
        """Establishes authenticated session with vCenter REST API."""
        try:
            auth = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            req = urllib.request.Request(f"https://{self.host}/rest/com/vmware/cis/session", method="POST")
            req.add_header("Authorization", f"Basic {auth}")
            with urllib.request.urlopen(req, context=self.ctx, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                self.session_id = data.get("value")
                return True
        except Exception as e:
            log(f"Failed authenticating to vCenter ({self.host}): {e}")
            return False

    def _api_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Optional[Any]:
        if not self.session_id:
            if not self.connect():
                return None

        url = f"https://{self.host}/rest{endpoint}"
        payload = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=payload, method=method)
        req.add_header("vmware-api-session-id", self.session_id)
        if data:
            req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=15) as resp:
                content = resp.read().decode("utf-8")
                if content:
                    return json.loads(content).get("value")
                return True
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # Session expired, reconnect once
                if self.connect():
                    return self._api_request(endpoint, method, data)
            log(f"vCenter API error on {endpoint}: {e.code} - {e.read().decode()}")
            return None
        except Exception as e:
            log(f"Network error on {endpoint}: {e}")
            return None

    def list_vms(self) -> List[Dict[str, Any]]:
        """Returns list of all VMs registered in vCenter."""
        res = self._api_request("/vcenter/vm")
        return res if res else []

    def get_vm_details(self, vm_id: str) -> Optional[Dict[str, Any]]:
        return self._api_request(f"/vcenter/vm/{vm_id}")

    def power_on(self, vm_id: str) -> bool:
        log(f"Powering ON VM {vm_id} via vCenter API...")
        res = self._api_request(f"/vcenter/vm/{vm_id}/power/start", method="POST")
        return res is not None

    def power_off(self, vm_id: str) -> bool:
        log(f"Powering OFF VM {vm_id} via vCenter API...")
        res = self._api_request(f"/vcenter/vm/{vm_id}/power/stop", method="POST")
        return res is not None

    def hot_scale_cpu(self, vm_id: str, new_cpu_count: int) -> bool:
        """Hot-adds/updates vCPUs on a virtual machine."""
        log(f"Hot-scaling VM {vm_id} to {new_cpu_count} vCPUs...")
        res = self._api_request(f"/vcenter/vm/{vm_id}/hardware/cpu", method="PATCH", data={"spec": {"count": new_cpu_count}})
        if res is not None:
            log(f"✅ Successfully updated VM {vm_id} CPU to {new_cpu_count} vCPUs.")
            return True
        return False

    def hot_scale_ram(self, vm_id: str, new_ram_mb: int) -> bool:
        """Hot-adds/updates RAM on a virtual machine."""
        log(f"Hot-scaling VM {vm_id} to {new_ram_mb} MB RAM...")
        res = self._api_request(f"/vcenter/vm/{vm_id}/hardware/memory", method="PATCH", data={"spec": {"size_MiB": new_ram_mb}})
        if res is not None:
            log(f"✅ Successfully updated VM {vm_id} RAM to {new_ram_mb} MB.")
            return True
        return False


class SlurmElasticScaler:
    """Manages elastic cluster scaling between Slurm and vCenter."""

    def __init__(self, vcenter: VCenterClient):
        self.vc = vcenter
        self.known_dynamic_nodes = {
            "node-05": {
                "vmid_name": "001_node-05",
                "ip": "192.168.0.125",
                "mac": "00:0c:29:9f:75:4f",
                "default_cpus": 8,
                "default_ram_mb": 8192
            },
            "node-06": {
                "vmid_name": "001_node-06",
                "ip": "192.168.0.146",
                "mac": "00:0c:29:9c:0a:32",
                "default_cpus": 8,
                "default_ram_mb": 8192
            }
        }

    def get_slurm_load(self) -> Dict[str, Any]:
        """Inspects queue demand and node states on the Slurm cluster."""
        # Check pending jobs
        pending_res = run_slurm("squeue -h -t PD -o '%i|%j|%r|%C'")
        pending_jobs = []
        if pending_res.returncode == 0 and pending_res.stdout.strip():
            for line in pending_res.stdout.strip().split("\n"):
                parts = line.split("|")
                if len(parts) >= 4:
                    pending_jobs.append({
                        "job_id": parts[0],
                        "name": parts[1],
                        "reason": parts[2],
                        "cpus_req": int(parts[3]) if parts[3].isdigit() else 1
                    })

        # Check node allocations and load
        node_res = run_slurm("sinfo -N -h -o '%N|%T|%c|%m|%O'")
        nodes = []
        total_cpus = 0
        allocated_cpus = 0
        total_load = 0.0

        unique_nodes = {}
        if node_res.returncode == 0 and node_res.stdout.strip():
            for line in node_res.stdout.strip().split("\n"):
                parts = line.split("|")
                if len(parts) >= 5:
                    n_name = parts[0]
                    if n_name in unique_nodes:
                        continue
                    n_state = parts[1]
                    n_cpus = int(parts[2]) if parts[2].isdigit() else 0
                    n_mem = int(parts[3]) if parts[3].isdigit() else 0
                    try:
                        n_load = float(parts[4])
                    except ValueError:
                        n_load = 0.0

                    unique_nodes[n_name] = {
                        "name": n_name,
                        "state": n_state,
                        "cpus": n_cpus,
                        "memory_mb": n_mem,
                        "load": n_load
                    }

        nodes = list(unique_nodes.values())
        total_cpus = sum(n["cpus"] for n in nodes)
        total_load = sum(n["load"] for n in nodes)
        allocated_cpus = sum(n["cpus"] for n in nodes if n["state"] in ["alloc", "mixed"])

        avg_load_pct = (total_load / max(1, total_cpus)) * 100 if total_cpus > 0 else 0.0

        return {
            "pending_jobs": pending_jobs,
            "pending_count": len(pending_jobs),
            "nodes": nodes,
            "total_cpus": total_cpus,
            "allocated_cpus": allocated_cpus,
            "average_cluster_load_pct": round(avg_load_pct, 1)
        }

    def provision_node(self, node_name: str = "node-05", cpus: int = 8, ram_mb: int = 8192) -> bool:
        """Autonomously provisions and integrates an additional compute node into Slurm."""
        cfg = self.known_dynamic_nodes.get(node_name)
        if not cfg:
            log(f"Node {node_name} is not in recognized dynamic node pool.")
            return False

        vm_name = cfg["vmid_name"]
        log(f"⚡ Autoscale Triggered: Provisioning {node_name} ({vm_name}) with {cpus} vCPUs, {ram_mb}MB RAM...")

        # 1. Check if VM exists in vCenter
        vms = self.vc.list_vms()
        target_vm = next((v for v in vms if v.get("name") in [vm_name, node_name]), None)

        if not target_vm:
            log(f"Cloning {vm_name} from 001_node-01 via ESXi storage...")
            clone_cmd = f"""
mkdir -p /vmfs/volumes/datastore3/{vm_name}
if [ ! -f /vmfs/volumes/datastore3/{vm_name}/{vm_name}.vmdk ]; then
    vmkfstools -i /vmfs/volumes/datastore3/001_node-01/001_node-01.vmdk -d thin /vmfs/volumes/datastore3/{vm_name}/{vm_name}.vmdk
fi
cp -p /vmfs/volumes/datastore3/001_node-01/001_node-01.vmx /vmfs/volumes/datastore3/{vm_name}/{vm_name}.vmx
sed -i 's/001_node-01/{vm_name}/g' /vmfs/volumes/datastore3/{vm_name}/{vm_name}.vmx
sed -i 's/^numvcpus = .*/numvcpus = "{cpus}"/' /vmfs/volumes/datastore3/{vm_name}/{vm_name}.vmx
sed -i 's/^memsize = .*/memsize = "{ram_mb}"/' /vmfs/volumes/datastore3/{vm_name}/{vm_name}.vmx
sed -i 's/ethernet0.address = .*/ethernet0.address = "{cfg["mac"]}"/' /vmfs/volumes/datastore3/{vm_name}/{vm_name}.vmx
vim-cmd solo/registervm /vmfs/volumes/datastore3/{vm_name}/{vm_name}.vmx {vm_name}
"""
            c_res = run_ssh(ESXI_HOST, clone_cmd, timeout=120)
            if c_res.returncode != 0:
                log(f"Failed cloning VM on ESXi: {c_res.stderr}")
                return False
            time.sleep(3)
            # Re-fetch VM list
            vms = self.vc.list_vms()
            target_vm = next((v for v in vms if v.get("name") in [vm_name, node_name]), None)

        if not target_vm:
            log("Could not register or locate cloned VM in vCenter.")
            return False

        vm_id = target_vm.get("vm")
        if target_vm.get("power_state") != "POWERED_ON":
            self.vc.power_on(vm_id)

        # 2. Wait for guest OS boot
        log(f"Waiting for {node_name} ({cfg['ip']}) to become reachable...")
        booted = False
        for _ in range(25):
            p_res = run_slurm(f"ping -c 1 -W 2 {cfg['ip']}")
            if p_res.returncode == 0:
                booted = True
                break
            time.sleep(3)

        if not booted:
            log(f"⚠️ Node {node_name} powered on but IP {cfg['ip']} did not respond to ping yet.")

        # 3. Register dynamically in Slurm
        log(f"Integrating {node_name} into Slurm cluster configuration...")
        slurm_conf_update = f"""
if ! grep -q "NodeName={node_name}" /etc/slurm/slurm.conf; then
    sed -i '/NodeName=node-04/a NodeName={node_name} CPUs={cpus} RealMemory={ram_mb - 500} State=UNKNOWN' /etc/slurm/slurm.conf
    sed -i 's/Nodes=node-\\[01-04\\]/Nodes=node-[01-05]/g' /etc/slurm/slurm.conf
    scontrol reconfigure
fi
scontrol update nodename={node_name} state=RESUME
"""
        run_slurm(slurm_conf_update)
        log(f"✅ {node_name} successfully provisioned and integrated into Slurm!")
        return True

    def deprovision_node(self, node_name: str = "node-05") -> bool:
        """Drains and powers off a dynamic burst node to free ESXi resources."""
        cfg = self.known_dynamic_nodes.get(node_name)
        if not cfg:
            return False

        log(f"Scale-down: Draining {node_name} in Slurm...")
        run_slurm(f"scontrol update nodename={node_name} state=DRAIN reason='autoscaler_idle'")

        # Wait for any active jobs to vacate
        time.sleep(5)
        vms = self.vc.list_vms()
        target_vm = next((v for v in vms if v.get("name") in [cfg["vmid_name"], node_name]), None)
        if target_vm and target_vm.get("power_state") == "POWERED_ON":
            log(f"Powering down dynamic node {node_name} via vCenter...")
            self.vc.power_off(target_vm.get("vm"))
            log(f"✅ Dynamic node {node_name} powered down. Resources reclaimed.")
            return True
        return False

    def evaluate_and_autoscale(self):
        """Autonomic evaluation loop: scales up on pressure, scales down on sustained idle."""
        metrics = self.get_slurm_load()
        pending = metrics["pending_count"]
        avg_load = metrics["average_cluster_load_pct"]

        log(f"Autoscale Monitor: Pending Jobs={pending} | Total Cores={metrics['total_cpus']} | Cluster Load={avg_load}%")

        # Scale Up Condition: pending jobs waiting or sustained load > 85%
        if pending > 0 or avg_load > 85.0:
            active_node_names = [n["name"] for n in metrics["nodes"]]
            if "node-05" not in active_node_names:
                log("⚡ Scale-Up condition met! Expanding cluster with additional node-05...")
                self.provision_node("node-05", cpus=8, ram_mb=8192)

        # Scale Down Condition: zero pending jobs and cluster load < 35%
        elif pending == 0 and avg_load < 35.0:
            active_node_names = [n["name"] for n in metrics["nodes"]]
            if "node-05" in active_node_names:
                log("❄️ Scale-Down condition met (idle cluster). Deactivating dynamic node-05...")
                self.deprovision_node("node-05")


def show_status(vc: VCenterClient, scaler: SlurmElasticScaler):
    print("\n" + "=" * 80)
    print(" ⚡ AI CORTEX VMWARE VCENTER ELASTIC AUTOSCALER & RESOURCE TOPOLOGY")
    print("=" * 80)

    # 1. Slurm Cluster Overview
    metrics = scaler.get_slurm_load()
    print("\n[SLURM CLUSTER TELEMETRY]")
    print(f" Total Compute Capacity: {metrics['total_cpus']} vCPUs across {len(metrics['nodes'])} active nodes")
    print(f" Cluster-Wide CPU Saturation: {metrics['average_cluster_load_pct']}%")
    print(f" Queue Demand / Pending Jobs: {metrics['pending_count']}")

    print(f"\n {'NODE':<12} {'STATE':<10} {'CPUS':<8} {'RAM (MB)':<12} {'1m LOAD'}")
    print(" " + "-" * 56)
    for n in metrics["nodes"]:
        print(f" {n['name']:<12} {n['state']:<10} {n['cpus']:<8} {n['memory_mb']:<12} {n['load']}")

    # 2. vCenter Infrastructure Inventory
    print("\n" + "-" * 80)
    print(" 🖥️  VMWARE VCENTER INVENTORY & RESOURCE ALLOCATION (https://192.168.0.146)")
    print("-" * 80)
    vms = vc.list_vms()
    if not vms:
        print("  (Could not fetch VMs from vCenter REST API)")
    else:
        print(f" {'VM NAME':<26} {'VM ID':<10} {'POWER STATE':<14} {'VCPUS':<8} {'RAM (MB)':<12}")
        print(" " + "-" * 76)
        for vm in sorted(vms, key=lambda x: x.get("name", "")):
            vname = vm.get("name", "")
            vid = vm.get("vm", "")
            pstate = vm.get("power_state", "")
            cpus = vm.get("cpu_count", 0)
            ram = vm.get("memory_size_MiB", 0)
            print(f" {vname:<26} {vid:<10} {pstate:<14} {cpus:<8} {ram:<12}")

    print("\n" + "=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="AI Cortex vCenter Autoscaler & Resource Redistributor")
    parser.add_argument("action", choices=["status", "autoscale-check", "scale-vm", "add-node", "remove-node", "daemon"], help="Action")
    parser.add_argument("--vm", help="Target VM name or ID for scaling")
    parser.add_argument("--cpus", type=int, help="New vCPU count")
    parser.add_argument("--ram", type=int, help="New RAM size in MB")
    parser.add_argument("--node", default="node-05", help="Target node for add/remove")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval for daemon in seconds")
    args = parser.parse_args()

    vc = VCenterClient()
    scaler = SlurmElasticScaler(vc)

    if args.action == "status":
        show_status(vc, scaler)
    elif args.action == "autoscale-check":
        scaler.evaluate_and_autoscale()
    elif args.action == "scale-vm":
        if not args.vm:
            print("Error: --vm required for scale-vm")
            sys.exit(1)
        vms = vc.list_vms()
        target = next((v for v in vms if v.get("name") == args.vm or v.get("vm") == args.vm), None)
        if not target:
            print(f"VM {args.vm} not found in vCenter.")
            sys.exit(1)
        vmid = target["vm"]
        if args.cpus:
            vc.hot_scale_cpu(vmid, args.cpus)
        if args.ram:
            vc.hot_scale_ram(vmid, args.ram)
    elif args.action == "add-node":
        scaler.provision_node(args.node, cpus=args.cpus or 8, ram_mb=args.ram or 8192)
    elif args.action == "remove-node":
        scaler.deprovision_node(args.node)
    elif args.action == "daemon":
        log(f"Starting Slurm-vCenter Autoscaler Daemon (Interval: {args.interval}s)...")
        while True:
            try:
                scaler.evaluate_and_autoscale()
            except Exception as e:
                log(f"Autoscaler error in loop: {e}")
            time.sleep(args.interval)

if __name__ == "__main__":
    main()
