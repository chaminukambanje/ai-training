#!/bin/bash
# Apple Silicon Mac LoRA fine-tuning with MLX
# Fast, low-memory, runs on M1/M2/M3/M4 unified memory in ~15 minutes.

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${DIR}/mlx_data"
OUTPUT_DIR="${DIR}/mlx_adapters"

mkdir -p "$DATA_DIR" "$OUTPUT_DIR"

echo "[+] Checking for mlx-lm..."
if ! python3 -c "import mlx_lm" &>/dev/null; then
    echo "Installing mlx-lm..."
    pip install -U mlx-lm
fi

# Convert training_dataset.jsonl to train.jsonl
echo "[+] Preparing dataset for MLX..."
cp "${DIR}/../data/training_dataset.jsonl" "${DATA_DIR}/train.jsonl"
head -n 5 "${DATA_DIR}/train.jsonl" > "${DATA_DIR}/valid.jsonl"

echo "[+] Launching MLX LoRA fine-tuning on Apple Silicon GPU..."
mlx_lm.lora \
    --model Qwen/Qwen2.5-7B-Instruct \
    --train \
    --data "$DATA_DIR" \
    --iters 300 \
    --batch-size 2 \
    --lora-layers 16 \
    --adapter-path "$OUTPUT_DIR"

echo "[+] Training complete! Adapter saved to $OUTPUT_DIR"
echo "[+] To fuse and export to GGUF for Ollama, run:"
echo "mlx_lm.fuse --model Qwen/Qwen2.5-7B-Instruct --adapter-path $OUTPUT_DIR --save-path ./fused_model --export-gguf"
