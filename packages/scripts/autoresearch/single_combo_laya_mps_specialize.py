"""Train a leakage-safe, head-only Laya reranker on Apple Silicon."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

FORMAT_VERSION = "single-combo-laya-mps-specialization-v3"
QUESTION_ID = "top3_combo"
NONE_OPTION = "NONE"
DEFAULT_MODEL_REVISION = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"
DEFAULT_MODEL_DIR = Path.home() / (
    ".cache/huggingface/hub/models--convaiinnovations--laya/snapshots/"
    f"{DEFAULT_MODEL_REVISION}/typed-decisions"
)
DEFAULT_TRAIN = Path(".cache/autoresearch/laya_specialization/train_augmented.jsonl")
DEFAULT_VALIDATION = Path(".cache/autoresearch/laya_temporal_dataset/validation.jsonl")
DEFAULT_OUTPUT_DIR = Path(".cache/autoresearch/laya_specialization/head_only_best")
DEFAULT_SEED = 20261001


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            rows.append(row)
    if not rows:
        raise ValueError(f"{path} contains no examples")
    return rows


def _race_id(row: dict[str, Any]) -> str:
    state = row.get("state")
    if not isinstance(state, dict) or not state.get("race_id"):
        raise ValueError("every row must contain state.race_id")
    return str(state["race_id"])


def _augmentation_index(row: dict[str, Any]) -> int:
    metadata = row.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("training rows must contain augmentation metadata")
    value = metadata.get("augmentation_index")
    if not isinstance(value, int) or value < 0:
        raise ValueError("augmentation_index must be a non-negative integer")
    return value


def validate_training_schedule(rows: list[dict[str, Any]]) -> dict[str, int]:
    by_race: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        race_id = _race_id(row)
        index = _augmentation_index(row)
        if index in by_race[race_id]:
            raise ValueError(f"duplicate augmentation {index} for race {race_id}")
        by_race[race_id].add(index)
    counts = {len(indices) for indices in by_race.values()}
    if len(counts) != 1:
        raise ValueError("every race must have the same augmentation count")
    augmentation_count = counts.pop()
    required = set(range(augmentation_count))
    if any(indices != required for indices in by_race.values()):
        raise ValueError("augmentation indices must be contiguous from zero")
    return {
        "independent_race_count": len(by_race),
        "augmentations_per_race": augmentation_count,
        "training_row_count": len(rows),
    }


def epoch_rows(
    rows: list[dict[str, Any]],
    *,
    epoch: int,
    augmentations_per_race: int,
) -> list[dict[str, Any]]:
    if epoch < 1:
        raise ValueError("epoch is one-based")
    selected_index = (epoch - 1) % augmentations_per_race
    selected = [row for row in rows if _augmentation_index(row) == selected_index]
    race_ids = [_race_id(row) for row in selected]
    if len(race_ids) != len(set(race_ids)):
        raise ValueError("an epoch may contain only one row per independent race")
    return sorted(selected, key=_race_id)


def limit_training_rows(
    rows: list[dict[str, Any]], max_train_races: int | None
) -> list[dict[str, Any]]:
    if max_train_races is None:
        return rows
    if max_train_races < 1:
        raise ValueError("max_train_races must be positive")
    retained_race_ids = sorted({_race_id(row) for row in rows})[:max_train_races]
    retained = set(retained_race_ids)
    return [row for row in rows if _race_id(row) in retained]


def _question(row: dict[str, Any]) -> dict[str, Any]:
    questions = row.get("questions")
    if not isinstance(questions, dict) or not isinstance(
        questions.get(QUESTION_ID), dict
    ):
        raise ValueError(f"row is missing question {QUESTION_ID}")
    return questions[QUESTION_ID]


def _target(row: dict[str, Any], labels: list[str]) -> tuple[list[float], str]:
    expected = row.get("expected")
    expected_label = expected.get(QUESTION_ID) if isinstance(expected, dict) else None
    gold = row.get("gold")
    gold_question = gold.get(QUESTION_ID) if isinstance(gold, dict) else None
    probabilities = (
        gold_question.get("probabilities") if isinstance(gold_question, dict) else None
    )
    if not isinstance(expected_label, str) or expected_label not in labels:
        raise ValueError("expected label must name one criterion")
    if isinstance(probabilities, dict):
        values = [float(probabilities.get(label, 0.0)) for label in labels]
    else:
        values = [float(label == expected_label) for label in labels]
    total = sum(values)
    if total <= 0.0 or not math.isfinite(total):
        raise ValueError("target probabilities must have positive finite mass")
    return [value / total for value in values], expected_label


def _build_item(
    row: dict[str, Any],
    *,
    tokenizer: Any,
    build_sequence: Any,
    qtypes: dict[str, int],
    max_len: int,
    head_max_len: int,
) -> dict[str, Any]:
    question = _question(row)
    criteria = question.get("criteria")
    if question.get("type") != "choice" or not isinstance(criteria, dict):
        raise ValueError("the specialization dataset must contain choice criteria")
    labels = list(criteria)
    target, expected_label = _target(row, labels)
    wire_question = {
        "t": "choice",
        "ins": str(question.get("instructions") or ""),
        "crit": criteria,
    }
    ids, markers, option_stats, truncation = build_sequence(
        tokenizer,
        row["state"],
        wire_question,
        max_len,
        head_max_len,
        return_stats=True,
        return_truncation_stats=True,
    )
    if len(markers) != len(labels):
        raise ValueError(f"{_race_id(row)} lost option markers during tokenization")
    if option_stats["options"] != option_stats["options_distinct"]:
        raise ValueError(f"{_race_id(row)} has collapsed option token spans")
    if truncation["truncated"]:
        raise ValueError(f"{_race_id(row)} has truncated state tokens")
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    return {
        "race_id": _race_id(row),
        "augmentation_index": metadata.get("augmentation_index"),
        "ids": ids,
        "markers": markers,
        "qtype": qtypes["choice"],
        "target": target,
        "expected_index": labels.index(expected_label),
        "expected_label": expected_label,
        "expected_description": str(criteria[expected_label]),
        "labels": labels,
        "descriptions": [str(criteria[label]) for label in labels],
    }


def _build_items(
    rows: list[dict[str, Any]],
    *,
    tokenizer: Any,
    build_sequence: Any,
    qtypes: dict[str, int],
    max_len: int,
    head_max_len: int,
) -> list[dict[str, Any]]:
    return [
        _build_item(
            row,
            tokenizer=tokenizer,
            build_sequence=build_sequence,
            qtypes=qtypes,
            max_len=max_len,
            head_max_len=head_max_len,
        )
        for row in rows
    ]


def _collate(items: list[dict[str, Any]], tokenizer: Any, torch: Any) -> dict[str, Any]:
    batch_size = len(items)
    sequence_length = max(len(item["ids"]) for item in items)
    option_count = max(len(item["markers"]) for item in items)
    input_ids = torch.full(
        (batch_size, sequence_length),
        tokenizer.pad_token_id,
        dtype=torch.long,
    )
    attention = torch.zeros((batch_size, sequence_length), dtype=torch.long)
    marker_pos = torch.zeros((batch_size, option_count), dtype=torch.long)
    marker_mask = torch.zeros((batch_size, option_count), dtype=torch.bool)
    target = torch.zeros((batch_size, option_count), dtype=torch.float32)
    for row_index, item in enumerate(items):
        length = len(item["ids"])
        input_ids[row_index, :length] = torch.tensor(item["ids"], dtype=torch.long)
        attention[row_index, :length] = 1
        count = len(item["markers"])
        marker_pos[row_index, :count] = torch.tensor(item["markers"], dtype=torch.long)
        marker_mask[row_index, :count] = True
        target[row_index, :count] = torch.tensor(item["target"], dtype=torch.float32)
    return {
        "input_ids": input_ids,
        "attention": attention,
        "marker_pos": marker_pos,
        "marker_mask": marker_mask,
        "target": target,
        "qtype": torch.tensor([item["qtype"] for item in items], dtype=torch.long),
    }


def _softmax(values: list[float], temperature: float) -> list[float]:
    scaled = [value / temperature for value in values]
    maximum = max(scaled)
    exponents = [math.exp(value - maximum) for value in scaled]
    total = sum(exponents)
    return [value / total for value in exponents]


def score_records(
    records: list[dict[str, Any]], temperature: float = 1.0
) -> dict[str, Any]:
    if not records:
        raise ValueError("cannot score an empty record set")
    correct = 0
    none_correct = 0
    none_count = 0
    candidate_correct = 0
    candidate_count = 0
    nll = 0.0
    confidences: list[tuple[float, int]] = []
    predicted_positions: Counter[str] = Counter()
    for record in records:
        probabilities = _softmax(record["logits"], temperature)
        predicted_index = max(range(len(probabilities)), key=probabilities.__getitem__)
        expected_index = int(record["expected_index"])
        is_correct = int(predicted_index == expected_index)
        correct += is_correct
        nll -= math.log(max(probabilities[expected_index], 1e-12))
        confidence = probabilities[predicted_index]
        confidences.append((confidence, is_correct))
        predicted_positions[str(predicted_index + 1)] += 1
        if record["expected_description"] == NONE_OPTION:
            none_count += 1
            none_correct += is_correct
        else:
            candidate_count += 1
            candidate_correct += is_correct
    ece = 0.0
    for bin_index in range(10):
        lower = bin_index / 10
        upper = (bin_index + 1) / 10
        bucket = [
            pair
            for pair in confidences
            if lower <= pair[0] < upper or (bin_index == 9 and pair[0] == 1.0)
        ]
        if not bucket:
            continue
        mean_confidence = sum(pair[0] for pair in bucket) / len(bucket)
        mean_accuracy = sum(pair[1] for pair in bucket) / len(bucket)
        ece += len(bucket) / len(confidences) * abs(mean_confidence - mean_accuracy)
    return {
        "race_count": len(records),
        "exact_accuracy": correct / len(records),
        "correct_count": correct,
        "top3_exact_accuracy": candidate_correct / len(records),
        "top3_correct_count": candidate_correct,
        "candidate_target_count": candidate_count,
        "candidate_target_accuracy": (
            candidate_correct / candidate_count if candidate_count else None
        ),
        "none_target_count": none_count,
        "none_target_accuracy": none_correct / none_count if none_count else None,
        "nll": nll / len(records),
        "mean_confidence": sum(pair[0] for pair in confidences) / len(confidences),
        "ece_10_bin": ece,
        "temperature": temperature,
        "predicted_position_distribution": dict(sorted(predicted_positions.items())),
    }


def fit_temperature(records: list[dict[str, Any]]) -> float:
    if len(records) < 10:
        return 1.0
    low = math.log(0.5)
    high = math.log(5.0)
    ratio = (math.sqrt(5.0) - 1.0) / 2.0

    def objective(log_temperature: float) -> float:
        return float(score_records(records, math.exp(log_temperature))["nll"])

    left = high - ratio * (high - low)
    right = low + ratio * (high - low)
    left_value = objective(left)
    right_value = objective(right)
    for _ in range(48):
        if left_value <= right_value:
            high = right
            right = left
            right_value = left_value
            left = high - ratio * (high - low)
            left_value = objective(left)
        else:
            low = left
            left = right
            left_value = right_value
            right = low + ratio * (high - low)
            right_value = objective(right)
    return min(5.0, max(0.5, math.exp((low + high) / 2.0)))


def _evaluate(
    model: Any,
    items: list[dict[str, Any]],
    *,
    tokenizer: Any,
    torch: Any,
    device: Any,
    batch_size: int,
) -> list[dict[str, Any]]:
    model.eval()
    records: list[dict[str, Any]] = []
    ordered = sorted(items, key=lambda item: len(item["ids"]))
    with torch.inference_mode():
        for start in range(0, len(ordered), batch_size):
            chunk = ordered[start : start + batch_size]
            batch = _collate(chunk, tokenizer, torch)
            logits, _activation = model(
                batch["input_ids"].to(device),
                batch["attention"].to(device),
                batch["marker_pos"].to(device),
                batch["marker_mask"].to(device),
                batch["qtype"].to(device),
                detach_encoder=True,
            )
            for index, item in enumerate(chunk):
                option_count = len(item["markers"])
                records.append(
                    {
                        "race_id": item["race_id"],
                        "logits": logits[index, :option_count].float().cpu().tolist(),
                        "expected_index": item["expected_index"],
                        "expected_label": item["expected_label"],
                        "expected_description": item["expected_description"],
                        "labels": item["labels"],
                        "descriptions": item["descriptions"],
                    }
                )
    return sorted(records, key=lambda record: record["race_id"])


def _train_epoch(
    model: Any,
    items: list[dict[str, Any]],
    *,
    epoch: int,
    epochs: int,
    tokenizer: Any,
    torch: Any,
    proper_reward: Any,
    optimizer: Any,
    scheduler: Any,
    device: Any,
    micro_batch: int,
    grad_accum: int,
    seed: int,
    train_encoder: bool,
) -> dict[str, float]:
    model.train()
    if not train_encoder:
        model.encoder.eval()
    shuffled = list(items)
    random.Random(seed + epoch).shuffle(shuffled)
    optimizer.zero_grad(set_to_none=True)
    sigma = 0.4 + (0.1 - 0.4) * (epoch - 1) / max(1, epochs - 1)
    totals: Counter[str] = Counter()
    batch_count = 0
    update_count = 0
    for start in range(0, len(shuffled), micro_batch):
        chunk = shuffled[start : start + micro_batch]
        batch = _collate(chunk, tokenizer, torch)
        input_ids = batch["input_ids"].to(device)
        attention = batch["attention"].to(device)
        marker_pos = batch["marker_pos"].to(device)
        marker_mask = batch["marker_mask"].to(device)
        target = batch["target"].to(device)
        qtype = batch["qtype"].to(device)
        logits, _activation = model(
            input_ids,
            attention,
            marker_pos,
            marker_mask,
            qtype,
            detach_encoder=not train_encoder,
        )
        logits = logits.float()
        option_count = marker_mask.sum(-1, keepdim=True).float()
        noise = torch.randn((4,) + logits.shape, device=device) * sigma
        noise = noise * marker_mask
        noise = (
            noise - noise.sum(-1, keepdim=True) / option_count.unsqueeze(0)
        ) * marker_mask
        noisy_logits = logits.detach().unsqueeze(0) + noise
        probabilities = torch.softmax(
            noisy_logits.masked_fill(~marker_mask, -1e4), dim=-1
        )
        with torch.no_grad():
            reward = proper_reward(
                probabilities,
                target.unsqueeze(0),
                qtype,
                marker_mask,
                w_sph=0.75,
                w_rps=1.0,
            )
            advantage = reward - reward.mean(0, keepdim=True)
            advantage = advantage / (advantage.std() + 1e-6)
        log_probability = -(
            ((noisy_logits - logits.unsqueeze(0)) ** 2) * marker_mask
        ).sum(-1) / (2 * sigma**2)
        loss_rl = -(advantage * log_probability).mean()
        loss_ce = (
            -(
                target
                * torch.log_softmax(logits.masked_fill(~marker_mask, -1e4), dim=-1)
            )
            .sum(-1)
            .mean()
        )
        loss = (loss_rl + loss_ce) / grad_accum
        loss.backward()
        batch_count += 1
        is_update = batch_count % grad_accum == 0 or start + micro_batch >= len(
            shuffled
        )
        if is_update:
            torch.nn.utils.clip_grad_norm_(
                [
                    parameter
                    for parameter in model.parameters()
                    if parameter.requires_grad
                ],
                1.0,
            )
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
            update_count += 1
        totals["loss"] += float((loss_rl + loss_ce).detach().cpu())
        totals["loss_ce"] += float(loss_ce.detach().cpu())
        totals["loss_rl"] += float(loss_rl.detach().cpu())
    return {
        "loss": totals["loss"] / batch_count,
        "loss_ce": totals["loss_ce"] / batch_count,
        "loss_rl": totals["loss_rl"] / batch_count,
        "sigma": sigma,
        "batch_count": float(batch_count),
        "update_count": float(update_count),
    }


def _trainable_state(model: Any) -> dict[str, Any]:
    return {
        name: parameter.detach().cpu().clone()
        for name, parameter in model.named_parameters()
        if parameter.requires_grad
    }


def _restore_trainable_state(model: Any, state: dict[str, Any]) -> None:
    parameters = dict(model.named_parameters())
    for name, value in state.items():
        parameters[name].data.copy_(
            value.to(device=parameters[name].device, dtype=parameters[name].dtype)
        )


def _is_better(candidate: dict[str, Any], incumbent: dict[str, Any]) -> bool:
    if candidate["top3_exact_accuracy"] != incumbent["top3_exact_accuracy"]:
        return candidate["top3_exact_accuracy"] > incumbent["top3_exact_accuracy"]
    if candidate["exact_accuracy"] != incumbent["exact_accuracy"]:
        return candidate["exact_accuracy"] > incumbent["exact_accuracy"]
    return candidate["nll"] < incumbent["nll"]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            probabilities = _softmax(
                record["logits"], float(record.get("temperature", 1.0))
            )
            predicted_index = max(
                range(len(probabilities)), key=probabilities.__getitem__
            )
            output = {
                "race_id": record["race_id"],
                "expected_label": record["expected_label"],
                "expected_description": record["expected_description"],
                "predicted_label": record["labels"][predicted_index],
                "predicted_description": record["descriptions"][predicted_index],
                "confidence": probabilities[predicted_index],
                "correct": predicted_index == record["expected_index"],
                "top3_correct": (
                    predicted_index == record["expected_index"]
                    and record["expected_description"] != NONE_OPTION
                ),
            }
            handle.write(
                json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n"
            )


def run(args: argparse.Namespace) -> dict[str, Any]:
    import torch
    from laya.common import QTYPES, build_model, build_sequence, proper_reward
    from safetensors.torch import load_file, save_file
    from transformers import AutoTokenizer

    started = time.time()
    model_dir = args.model_dir.resolve()
    if not (model_dir / "model.safetensors").exists():
        raise FileNotFoundError(f"Laya checkpoint not found: {model_dir}")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    train_rows = limit_training_rows(
        _load_jsonl(args.train),
        args.max_train_races,
    )
    validation_rows = _load_jsonl(args.validation)
    schedule = validate_training_schedule(train_rows)
    validation_race_ids = {_race_id(row) for row in validation_rows}
    train_race_ids = {_race_id(row) for row in train_rows}
    overlap = sorted(train_race_ids & validation_race_ids)
    if overlap:
        raise ValueError(f"train/validation race overlap: {overlap[:5]}")

    config = json.loads((model_dir / "rl_agent_config.json").read_text())
    config["max_len"] = args.max_len
    config["head_max_len"] = args.head_max_len
    tokenizer = AutoTokenizer.from_pretrained(model_dir / "tokenizer")
    train_items = _build_items(
        train_rows,
        tokenizer=tokenizer,
        build_sequence=build_sequence,
        qtypes=QTYPES,
        max_len=args.max_len,
        head_max_len=args.head_max_len,
    )
    validation_items = _build_items(
        validation_rows,
        tokenizer=tokenizer,
        build_sequence=build_sequence,
        qtypes=QTYPES,
        max_len=args.max_len,
        head_max_len=args.head_max_len,
    )
    model = build_model(config, encoder_dir=model_dir / "encoder")
    model.load_state_dict(load_file(str(model_dir / "model.safetensors")), strict=True)
    model.float()
    train_encoder = args.encoder_learning_rate > 0.0
    if train_encoder:
        model.encoder.gradient_checkpointing_enable(
            gradient_checkpointing_kwargs={"use_reentrant": False}
        )
        model.head_checkpointing = True
    for name, parameter in model.named_parameters():
        parameter.requires_grad = not name.startswith("act_head.") and (
            train_encoder or not name.startswith("encoder.")
        )
    device_name = args.device
    if device_name == "auto":
        device_name = "mps" if torch.backends.mps.is_available() else "cpu"
    if device_name == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS was requested but is unavailable")
    device = torch.device(device_name)
    torch.manual_seed(args.seed)
    model.to(device)

    baseline_records = _evaluate(
        model,
        validation_items,
        tokenizer=tokenizer,
        torch=torch,
        device=device,
        batch_size=args.eval_batch,
    )
    baseline_metrics = score_records(baseline_records)
    _write_json(output_dir / "zero_shot_validation.json", baseline_metrics)
    print(
        json.dumps(
            {"stage": "zero_shot", **baseline_metrics},
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )

    named_parameters = list(model.named_parameters())
    encoder_parameters = [
        parameter
        for name, parameter in named_parameters
        if name.startswith("encoder.") and parameter.requires_grad
    ]
    head_parameters = [
        parameter
        for name, parameter in named_parameters
        if not name.startswith("encoder.") and parameter.requires_grad
    ]
    optimizer_groups = [{"params": head_parameters, "lr": args.learning_rate}]
    if encoder_parameters:
        optimizer_groups.insert(
            0,
            {"params": encoder_parameters, "lr": args.encoder_learning_rate},
        )
    optimizer = torch.optim.AdamW(optimizer_groups, weight_decay=args.weight_decay)
    batches_per_epoch = math.ceil(schedule["independent_race_count"] / args.micro_batch)
    updates_per_epoch = math.ceil(batches_per_epoch / args.grad_accum)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=max(1, updates_per_epoch * args.epochs),
        eta_min=1e-6 if train_encoder else args.learning_rate * 0.1,
    )

    best_epoch = 0
    best_metrics = baseline_metrics
    best_state = _trainable_state(model)
    history: list[dict[str, Any]] = []
    items_by_key = {
        (item["race_id"], item["augmentation_index"]): item for item in train_items
    }
    for epoch in range(1, args.epochs + 1):
        selected_rows = epoch_rows(
            train_rows,
            epoch=epoch,
            augmentations_per_race=schedule["augmentations_per_race"],
        )
        selected_items = [
            items_by_key[(_race_id(row), _augmentation_index(row))]
            for row in selected_rows
        ]
        training_metrics = _train_epoch(
            model,
            selected_items,
            epoch=epoch,
            epochs=args.epochs,
            tokenizer=tokenizer,
            torch=torch,
            proper_reward=proper_reward,
            optimizer=optimizer,
            scheduler=scheduler,
            device=device,
            micro_batch=args.micro_batch,
            grad_accum=args.grad_accum,
            seed=args.seed,
            train_encoder=train_encoder,
        )
        validation_records = _evaluate(
            model,
            validation_items,
            tokenizer=tokenizer,
            torch=torch,
            device=device,
            batch_size=args.eval_batch,
        )
        validation_metrics = score_records(validation_records)
        entry = {
            "epoch": epoch,
            "augmentation_index": (epoch - 1) % schedule["augmentations_per_race"],
            "training": training_metrics,
            "validation": validation_metrics,
        }
        history.append(entry)
        if _is_better(validation_metrics, best_metrics):
            best_epoch = epoch
            best_metrics = validation_metrics
            best_state = _trainable_state(model)
        _write_json(
            output_dir / "run_progress.json",
            {
                "format_version": FORMAT_VERSION,
                "best_epoch": best_epoch,
                "best_validation": best_metrics,
                "history": history,
            },
        )
        print(json.dumps(entry, ensure_ascii=False, sort_keys=True), flush=True)

    _restore_trainable_state(model, best_state)
    final_records = _evaluate(
        model,
        validation_items,
        tokenizer=tokenizer,
        torch=torch,
        device=device,
        batch_size=args.eval_batch,
    )
    temperature = fit_temperature(final_records)
    calibrated_metrics = score_records(final_records, temperature)
    for record in final_records:
        record["temperature"] = temperature
    _write_records(output_dir / "validation_predictions.jsonl", final_records)

    original_temperatures = config.get("temperature", [1.0, 1.0, 1.0])
    if not isinstance(original_temperatures, list) or len(original_temperatures) != 3:
        original_temperatures = [1.0, 1.0, 1.0]
    config["temperature"] = [
        temperature,
        float(original_temperatures[1]),
        float(original_temperatures[2]),
    ]
    config.pop("temperature_by_options", None)
    config["fine_tuned"] = True
    config["training"] = {
        "method": (
            "full_encoder_one_option_order_per_race_per_epoch"
            if train_encoder
            else "head_only_one_option_order_per_race_per_epoch"
        ),
        "independent_race_count": schedule["independent_race_count"],
        "augmentations_per_race": schedule["augmentations_per_race"],
        "epochs_completed": args.epochs,
        "best_epoch": best_epoch,
        "learning_rate": args.learning_rate,
        "encoder_learning_rate": args.encoder_learning_rate,
        "weight_decay": args.weight_decay,
        "micro_batch": args.micro_batch,
        "grad_accum": args.grad_accum,
        "seed": args.seed,
    }
    weights = {
        name: value.detach().half().cpu().contiguous()
        for name, value in model.state_dict().items()
    }
    save_file(weights, str(output_dir / "model.safetensors"))
    model.encoder.config.save_pretrained(output_dir / "encoder")
    tokenizer.save_pretrained(output_dir / "tokenizer")
    _write_json(output_dir / "rl_agent_config.json", config)

    manifest = {
        "format_version": FORMAT_VERSION,
        "status": "passed",
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "final_test_inference_run": False,
        "final_test_labels_used_for_selection": False,
        "base_model_revision": DEFAULT_MODEL_REVISION,
        "base_model_dir": str(model_dir),
        "base_model_sha256": _sha256_file(model_dir / "model.safetensors"),
        "train_path": str(args.train),
        "train_sha256": _sha256_file(args.train),
        "validation_path": str(args.validation),
        "validation_sha256": _sha256_file(args.validation),
        "schedule": schedule,
        "max_train_races": args.max_train_races,
        "training_mode": "full_encoder" if train_encoder else "head_only",
        "trainable_parameter_count": sum(
            parameter.numel()
            for parameter in model.parameters()
            if parameter.requires_grad
        ),
        "max_len": args.max_len,
        "head_max_len": args.head_max_len,
        "device": str(device),
        "zero_shot_validation": baseline_metrics,
        "best_epoch": best_epoch,
        "best_validation_uncalibrated": score_records(final_records),
        "best_validation_calibrated": calibrated_metrics,
        "history": history,
        "checkpoint_sha256": _sha256_file(output_dir / "model.safetensors"),
        "elapsed_seconds": round(time.time() - started, 3),
        "recommended_next_action": (
            "run_validation_order_sensitivity_before_unsealing_test"
        ),
    }
    _write_json(output_dir / "run_manifest.json", manifest)
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--device", default="auto", choices=("auto", "mps", "cpu"))
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--micro-batch", type=int, default=1)
    parser.add_argument("--eval-batch", type=int, default=4)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--encoder-learning-rate", type=float, default=0.0)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--max-len", type=int, default=1024)
    parser.add_argument("--head-max-len", type=int, default=512)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--max-train-races", type=int)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if min(args.epochs, args.micro_batch, args.eval_batch, args.grad_accum) < 1:
        raise ValueError("epoch and batch arguments must be positive")
    if args.learning_rate <= 0.0 or args.encoder_learning_rate < 0.0:
        raise ValueError("learning rates must be positive or zero for a frozen encoder")
    if args.max_train_races is not None and args.max_train_races < 1:
        raise ValueError("max_train_races must be positive")
    manifest = run(args)
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
