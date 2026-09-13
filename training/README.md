# AI Cortex Continuous Learning & Fine-Tuning Guide

This directory manages dataset harvesting and LoRA fine-tuning for **AI Cortex** (`qwen2.5:7b`).

---

## 1. How Knowledge Distillation Works
1. **Automated Harvesting**:
   When queries pass through the AI Cortex Gateway (`http://192.168.0.235:8000/v1/chat/completions`), verified answers (or grounding results) are appended in real-time to:
   `/opt/ai-cortex/data/training_dataset.jsonl`
2. **Standard Format**:
   Data is stored in ChatML format:
   ```json
   {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
   ```
3. **Model Re-training**:
   As new homelab infrastructure, services, or verified facts are added, you can periodically run the fine-tuning script to update the model weights.

---

## 2. Option A: Training on Apple Silicon Mac (Recommended for Speed)
Apple Silicon Macs have unified memory and fast Neural/Metal GPUs:
1. Sync the dataset from `ai-cortex-01` to your Mac:
   ```bash
   scp mbanjec@192.168.0.235:/opt/ai-cortex/data/training_dataset.jsonl ~/ai-cortex-data/
   ```
2. Run MLX fine-tuning:
   ```bash
   bash /opt/ai-cortex/training/train_mlx.sh
   ```
3. Fine-tuning takes ~10–15 minutes. Export the adapter to GGUF and import into Ollama:
   ```bash
   ollama create ai-cortex:v2 -f Modelfile
   ```

---

## 3. Option B: Training Directly on AI Server / Slurm Cluster
To run on the local server or a Slurm compute node:
```bash
/opt/ai-cortex/venv/bin/python3 /opt/ai-cortex/training/train_lora.py \
    --dataset_path /opt/ai-cortex/data/training_dataset.jsonl \
    --output_dir /opt/ai-cortex/training/output_lora \
    --num_epochs 3
```

---

## 4. Baked Persona (Modelfile)
The immediate custom model is defined at:
`/opt/ai-cortex/Modelfile`

To rebuild or update the model persona at any time:
```bash
ollama create ai-cortex -f /opt/ai-cortex/Modelfile
```
Test with:
```bash
ollama run ai-cortex "Who owns this homelab and what are the ESXi specs?"
```
