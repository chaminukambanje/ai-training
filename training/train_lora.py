#!/usr/bin/env python3
"""
LoRA Fine-Tuning Pipeline for AI Cortex (Qwen 2.5 7B)
Using Hugging Face Transformers, PEFT, and TRL.
"""

import os
import sys
import argparse
from datasets import load_dataset
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer

def main():
    parser = argparse.ArgumentParser(description="Fine-tune Qwen 2.5 7B with LoRA")
    parser.add_argument("--model_name_or_path", type=str, default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--dataset_path", type=str, default="/opt/ai-cortex/data/training_dataset.jsonl")
    parser.add_argument("--output_dir", type=str, default="/opt/ai-cortex/training/output_lora")
    parser.add_argument("--num_epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--grad_accum", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-4)
    args = parser.parse_args()

    if not os.path.exists(args.dataset_path):
        print(f"Error: Dataset {args.dataset_path} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"[+] Loading dataset: {args.dataset_path}")
    dataset = load_dataset("json", data_files=args.dataset_path, split="train")

    print(f"[+] Loading tokenizer: {args.model_name_or_path}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    print(f"[+] Formatting dataset using Qwen chat template...")
    def format_chat(sample):
        text = tokenizer.apply_chat_template(sample["messages"], tokenize=False)
        return {"text": text}

    formatted_dataset = dataset.map(format_chat)

    print(f"[+] Loading base model: {args.model_name_or_path}")
    device_map = "auto" if torch.cuda.is_available() else None
    torch_dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

    model = AutoModelForCausalLM.from_pretrained(
        args.model_name_or_path,
        torch_dtype=torch_dtype,
        device_map=device_map,
        trust_remote_code=True,
    )

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        num_train_epochs=args.num_epochs,
        logging_steps=5,
        save_strategy="epoch",
        fp16=False,
        bf16=torch.cuda.is_available(),
        optim="adamw_torch",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=formatted_dataset,
        dataset_text_field="text",
        max_seq_length=1024,
        tokenizer=tokenizer,
        args=training_args,
    )

    print("[+] Starting LoRA fine-tuning...")
    trainer.train()

    print(f"[+] Saving fine-tuned LoRA adapter to {args.output_dir}...")
    trainer.model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print("[+] Fine-tuning complete! Next step: merge adapter or load in Ollama via Modelfile.")

if __name__ == "__main__":
    main()
