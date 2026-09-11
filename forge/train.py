"""Unsloth LoRA on the base named in task.yaml, held-out eval over the label tokens only,
GGUF q4_k_m export, the LoRA adapter, model-card.yaml and eval.json. Refuses under min_agreement.

    python train.py [--task task.yaml] [--data dataset.jsonl] [--out artifact] [--max-steps N]
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess  # noqa: S404  llama.cpp's own converter and quantiser, argv lists only
import sys

import torch
import yaml
from datasets import load_dataset

from common import envelope, frontier, grade, label_probs, majority_agreement, next_move

# Where forge/modal_app.py bakes llama.cpp into the image; a laptop run points it elsewhere.
LLAMA_CPP_DIR = os.environ.get("LLAMA_CPP_DIR", "/opt/llama.cpp")


def export_gguf(model, tokenizer, out: str) -> None:
    """Merged 16-bit weights, then llama.cpp's converter and quantiser, called directly.

    Not `model.save_pretrained_gguf(...)`: that clones and builds llama.cpp during the run and
    asks the terminal to approve an apt-get first. On a headless GPU container the prompt reads
    EOF and the export raises, which is how run 34401515600 (2026-09-09) finished training,
    passed both gates at agreement 0.9773 and abstain 0.175, and still published nothing --
    "RuntimeError: Unsloth: GGUF conversion failed: EOF when reading a line".
    """
    merged = os.path.join(out, "merged")
    model.save_pretrained_merged(merged, tokenizer, save_method="merged_16bit")

    # THE TOKENIZER, PASSED EXPLICITLY, AND THIS IS THE BUG THAT ATE EVERY ARTIFACT.
    #
    # `convert_hf_to_gguf.py` looks for `tokenizer.model` -- a SentencePiece file -- and Qwen2 does
    # not have one. It uses a BPE `tokenizer.json`, which `save_pretrained_merged` writes and the
    # converter does not look for by default. So the export died with
    #     FileNotFoundError: File not found: artifact/merged/tokenizer.model
    # AFTER both quality gates had passed. Run 34597942691: agreement 0.9846 against a 0.95 gate,
    # abstain 0.1875 against 0.20 -- and artifact=None.
    #
    # `--vocab-only` would write a tokenizer rather than read the right one; `--tokenizer-json`
    # points the converter at the file that exists. Named here rather than guessed: if neither file
    # is present the export fails loudly below instead of producing a model that cannot tokenise.
    tokenizer_json = os.path.join(merged, "tokenizer.json")
    if not os.path.exists(tokenizer_json):
        raise RuntimeError(
            f"no tokenizer.json in {merged}: the merged model cannot be converted, and a GGUF "
            "without a tokenizer is a model that answers nothing"
        )

    f16 = os.path.join(out, "model-f16.gguf")
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            os.path.join(LLAMA_CPP_DIR, "convert_hf_to_gguf.py"),
            merged,
            "--outfile",
            f16,
            "--outtype",
            "f16",
            "--tokenizer-json",
            tokenizer_json,
        ],
        check=True,
    )
    subprocess.run(  # noqa: S603
        [
            os.path.join(LLAMA_CPP_DIR, "build", "bin", "llama-quantize"),
            f16,
            os.path.join(out, "model.gguf"),
            "Q4_K_M",
        ],
        check=True,
    )
    # The f16 intermediate is ~3 GB and the merged weights the same again; neither is part of
    # the artifact, and both would otherwise ride into the oras push.
    os.remove(f16)
    shutil.rmtree(merged, ignore_errors=True)


def predict(
    model, tokenizer, eval_ds, template, label_ids
) -> list[tuple[str, str, float]]:
    """(expected, predicted, margin) for every held-out row, the same arithmetic the Runtime
    uses: softmax over the label tokens only. Called twice -- before training and after -- so
    the record can say what training bought instead of asserting that it bought something."""
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
    return rows


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
    label_ids = {
        lab: tokenizer.encode(lab, add_special_tokens=False)[0]
        for lab in task["labels"]
    }
    # The control, before a single gradient step. A LoRA is zero-initialised, so the model
    # here answers exactly as the untrained base does; without this reading nothing in the
    # record can distinguish a model that learned the task from one that guessed well.
    FastLanguageModel.for_inference(model)
    base_rows = predict(model, tokenizer, eval_ds, template, label_ids)
    FastLanguageModel.for_training(model)

    trainer.train()

    FastLanguageModel.for_inference(model)
    rows = predict(model, tokenizer, eval_ds, template, label_ids)
    result = grade(rows, task["abstain_below"])
    # What it can do, what it cannot do reliably, where the edge is, and which lever moves it
    result["envelope"] = envelope(rows, task["abstain_below"])
    result["envelope"]["agreement_answered"] = result["agreement"]
    result["frontier"] = frontier(rows)
    result["majority"] = majority_agreement(rows)
    baseline = grade(base_rows, task["abstain_below"])
    baseline["envelope"] = envelope(base_rows, task["abstain_below"])
    result["baseline"] = baseline
    result["lift_over_untrained"] = result["agreement"] - baseline["agreement"]
    result["lift_over_majority"] = result["agreement"] - result["majority"]["agreement"]
    result["next_move"] = next_move(
        result["envelope"], result["frontier"], task, baseline
    )
    refusal = None
    if result["agreement"] < task["min_agreement"]:
        refusal = f"held-out agreement {result['agreement']:.4f} below {task['min_agreement']}"
    elif result["abstain_rate"] > task["max_abstain"]:
        refusal = f"held-out abstain rate {result['abstain_rate']:.4f} above {task['max_abstain']}"
    elif task.get("min_lift_over_majority") is not None and (
        result["lift_over_majority"] < task["min_lift_over_majority"]
    ):
        refusal = (
            f"lift over always answering `{result['majority']['label']}` "
            f"{result['lift_over_majority']:.4f} below {task['min_lift_over_majority']}"
        )
    elif task.get("min_recall_per_label") is not None and (
        thin := [
            lab
            for lab, r in sorted(result["envelope"]["per_label"].items())
            if r["recall_answered"] is not None
            and r["recall_answered"] < task["min_recall_per_label"]
        ]
    ):
        refusal = (
            f"labels {thin} are caught below {task['min_recall_per_label']} of the time; "
            "a model blind to a label is not useful on it"
        )
    result["verdict"] = "refused" if refusal else "passed"
    result["refusal"] = refusal
    with open(args.data, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    dataset_meta = {
        "rows": len(dataset),
        "train": len(train_ds),
        "eval": len(eval_ds),
        "sha256": digest,
        "langfuse_dataset": task["task"],
    }
    result["dataset"] = dataset_meta
    print(json.dumps(result))
    # eval.json is written on EVERY run, refused or not: a refusal is a result, and the
    # experiment record (forge/experiments/) keeps it. Only the model waits on the gates.
    shutil.rmtree(args.out, ignore_errors=True)
    os.makedirs(args.out)
    with open(os.path.join(args.out, "eval.json"), "w", encoding="utf-8") as f:
        json.dump(result, f)
    if refusal:
        raise SystemExit(f"Refusal: {refusal}")

    export_gguf(model, tokenizer, args.out)
    tokenizer.save_pretrained(args.out)  # tokenizer.json, read by the Runtime
    # the adapter alone, a few MB: re-export at another quantisation, merge with other tasks'
    # adapters, or serve per client without a second copy of the base (adopt note 2026-09-06)
    model.save_pretrained(os.path.join(args.out, "adapter"))
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
    card["dataset"] = dataset_meta
    with open(os.path.join(args.out, "model-card.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(card, f, sort_keys=False)


if __name__ == "__main__":
    main()
