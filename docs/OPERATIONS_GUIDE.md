# AI Cortex Operations & Administration Guide

This guide covers operational administration, systemd service management, CLI tooling, and troubleshooting for the AI Cortex Autonomous Learning Pipeline.

---

## 1. Systemd Services Management

The environment relies on three primary systemd services on `ai-cortex-01`:

```
┌─────────────────────────┐
│     ollama.service      │ ─── Inference Engine (Port 11434)
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│    ai-cortex.service    │ ─── FastAPI Grounding & RAG Gateway (Port 8000)
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│ ai-docs-trainer.service │ ─── Autonomous Documentation Learning Daemon
└─────────────────────────┘
```

### Common Service Commands:
```bash
# Check service statuses
sudo systemctl status ai-cortex
sudo systemctl status ai-docs-trainer
sudo systemctl status ollama

# Restart services
sudo systemctl restart ai-cortex
sudo systemctl restart ai-docs-trainer
sudo systemctl restart ollama

# View service logs
sudo journalctl -u ai-docs-trainer -f
sudo journalctl -u ai-cortex -f
```

---

## 2. The `ai-trainer` CLI Utility

Installed at `/usr/local/bin/ai-trainer`:

### `ai-trainer status`
Displays the active status of `ai-docs-trainer.service`, live telemetry from the `/health` endpoint, and loaded Ollama models.

### `ai-trainer cycle`
Manually triggers an immediate learning cycle without waiting for the 30-minute timer. Harvests new pages, indexes chunks into SQLite, synthesizes new instruction pairs, and recompiles the Ollama model.

### `ai-trainer logs`
Follows the persistent learning log located at `/opt/ai-cortex/data/training_learner.log`.

### `ai-trainer ask "<query>"`
Executes a test query through the grounding gateway and prints the model's response directly to the terminal.

---

## 3. Storage & Resource Allocation

* **Knowledge Database**: `/opt/ai-cortex/knowledge/cortex_knowledge.db` (SQLite WAL mode).
* **Raw Harvested Docs**: `/opt/ai-cortex/knowledge/raw/<domain>/`.
* **Instruction Dataset**: `/opt/ai-cortex/data/training_dataset.jsonl`.
* **Modelfile**: `/opt/ai-cortex/Modelfile`.
* **Hardware Specs**: 16 vCPUs, 43 GB RAM allocated on ESXi host `esxi-01.npcsolutions.co.za` (VMID 108).
* **Storage Consumption**: ~10 MB for datasets, ~50 MB for knowledge databases and raw documents.

---

## 4. Fine-Tuning with LoRA (Optional)

When desired, the synthesized dataset can be used to fine-tune a custom adapter using Hugging Face PEFT/TRL or MLX on Apple Silicon:

### Linux / Server Fine-Tuning:
```bash
/opt/ai-cortex/venv/bin/python3 /opt/ai-cortex/training/train_lora.py \
    --dataset_path /opt/ai-cortex/data/training_dataset.jsonl \
    --output_dir /opt/ai-cortex/training/output_lora \
    --num_epochs 3
```

### Apple Silicon Mac Fine-Tuning (MLX):
```bash
scp mbanjec@192.168.0.235:/opt/ai-cortex/data/training_dataset.jsonl ~/ai-cortex-data/
bash training/train_mlx.sh
```
