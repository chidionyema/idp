"""Unsloth LoRA on the base named in task.yaml, held-out eval over the label tokens only,
GGUF q4_k_m export, model-card.yaml and eval.json. Refuses under min_agreement.

    python train.py [--task task.yaml] [--data dataset.jsonl] [--out artifact] [--max-steps N]
"""

import argparse
import hashlib
import json
import os
import shutil

import torch
import yaml
from datasets import load_dataset

from common import grade, label_probs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="task.yaml")
    ap.add_argument("--data", default="dataset.jsonl")
    ap.add_argument("--out", default="artifact")
    ap.add_argument(
        "--max-steps", type=int, default=-1, help="fixture runs: cap the steps"
    )
    args = ap.parse_args()

    from unsloth import FastLanguageModel, is_bfloat16_supported
    from transformers import TrainingArguments
    from trl import SFTTrainer

    with open(args.task, encoding="utf-8") as f:
        task = yaml.safe_load(f)
    max_seq_length = 2048
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=task["base"],
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=task["lora"]["r"],
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_alpha=task["lora"]["alpha"],
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    dataset = load_dataset("json", data_files=args.data, split="train")
    train_ds = dataset.filter(lambda x: x["split"] == "train")
    eval_ds = dataset.filter(lambda x: x["split"] == "eval")
    template = task["prompt_template"]

    def format_row(row):
        return {
            "text": template.replace("{input}", row["input"])
            + row["output"]
            + tokenizer.eos_token
        }

    train_ds = train_ds.map(format_row)
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        args=TrainingArguments(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=10,
            num_train_epochs=task["lora"]["epochs"],
            max_steps=args.max_steps,
            learning_rate=float(task["lora"]["lr"]),
            fp16=not is_bfloat16_supported(),
            bf16=is_bfloat16_supported(),
            logging_steps=10,
            optim="adamw_8bit",
            output_dir="outputs",
            seed=3407,
            report_to="none",
        ),
    )
    trainer.train()

    # Held-out eval, the same arithmetic the Runtime uses: softmax over the label tokens only.
    FastLanguageModel.for_inference(model)
    label_ids = {
        lab: tokenizer.encode(lab, add_special_tokens=False)[0]
        for lab in task["labels"]
    }
    rows = []
    for row in eval_ds:
        inputs = tokenizer(
            [template.replace("{input}", row["input"])], return_tensors="pt"
        ).to("cuda")
        with torch.no_grad():
            logits = model(**inputs).logits[0, -1]
        top, _, margin = label_probs(
            {lab: float(logits[tid]) for lab, tid in label_ids.items()}
        )
        rows.append((row["output"], top, margin))
    result = grade(rows, task["abstain_below"])
    print(json.dumps(result))
    if result["agreement"] < task["min_agreement"]:
        raise SystemExit(
            f"Refusal: held-out agreement {result['agreement']:.4f} below {task['min_agreement']}"
        )
    if result["abstain_rate"] > task["max_abstain"]:
        raise SystemExit(
            f"Refusal: held-out abstain rate {result['abstain_rate']:.4f} above {task['max_abstain']}"
        )

    shutil.rmtree(args.out, ignore_errors=True)
    os.makedirs(args.out)
    model.save_pretrained_gguf(args.out, tokenizer, quantization_method="q4_k_m")
    gguf = next(n for n in os.listdir(args.out) if n.endswith(".gguf"))
    os.replace(os.path.join(args.out, gguf), os.path.join(args.out, "model.gguf"))
    tokenizer.save_pretrained(args.out)  # tokenizer.json, read by the Runtime
    card = {
        k: task[k]
        for k in (
            "task",
            "base",
            "kind",
            "prompt_template",
            "labels",
            "abstain_below",
            "min_agreement",
            "max_abstain",
            "kv_cache_prefix",
            "schema",
        )
    }
    card["eval"] = result
    # The training data travels with the model: the file itself and its hash in the card.
    shutil.copy(args.data, os.path.join(args.out, "dataset.jsonl"))
    with open(args.data, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    card["dataset"] = {
        "rows": len(dataset),
        "train": len(train_ds),
        "eval": len(eval_ds),
        "sha256": digest,
        "langfuse_dataset": task["task"],
    }
    with open(os.path.join(args.out, "model-card.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(card, f, sort_keys=False)
    with open(os.path.join(args.out, "eval.json"), "w", encoding="utf-8") as f:
        json.dump(result, f)


if __name__ == "__main__":
    main()
