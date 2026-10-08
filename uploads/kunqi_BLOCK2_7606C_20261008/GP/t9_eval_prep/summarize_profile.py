#!/usr/bin/env python3
"""Validate T9 v0.3 events against the adjacent schema (Python 3.10+, stdlib only)."""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"Non-finite JSON: {x}")))


def schema_errors(value, schema, path="$", root=None):
    """Small interpreter for precisely the keywords used by our shipped schema.

    Unknown validation keywords fail closed; this is NOT a general JSON Schema engine.
    The schema is also usable with standard Draft 2020-12 validators.
    """
    root = schema if root is None else root
    supported = {"$schema", "$id", "title", "description", "$defs", "$ref", "type", "enum",
                 "const", "required", "properties", "additionalProperties", "items", "minItems",
                 "uniqueItems", "minLength", "minimum", "exclusiveMinimum", "maximum", "allOf",
                 "if", "then", "else"}
    unknown = set(schema) - supported
    if unknown:
        raise ValueError(f"Unsupported schema keywords: {sorted(unknown)}")
    errors = []
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            raise ValueError("Only local schema references are supported")
        target = root
        for part in ref[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        errors += schema_errors(value, target, path, root)
    for sub in schema.get("allOf", []):
        errors += schema_errors(value, sub, path, root)
    if "if" in schema:
        branch = "else" if schema_errors(value, schema["if"], path, root) else "then"
        errors += schema_errors(value, schema.get(branch, {}), path, root)
    number = isinstance(value, (float, int)) and not isinstance(value, bool)
    finite = number and math.isfinite(value)
    matches = {"null": value is None, "object": isinstance(value, dict), "array": isinstance(value, list),
               "string": isinstance(value, str), "boolean": isinstance(value, bool),
               "integer": finite and float(value).is_integer(), "number": finite}
    types = schema.get("type", [])
    types = [types] if isinstance(types, str) else types
    if types and not any(matches[t] for t in types):
        return errors + [f"{path}: expected {types}"]
    def equal(a, b):
        if isinstance(a, bool) != isinstance(b, bool):
            return False
        return a == b
    if "enum" in schema and not any(equal(value, x) for x in schema["enum"]):
        errors.append(f"{path}: invalid enum value {value!r}")
    if "const" in schema and not equal(value, schema["const"]):
        errors.append(f"{path}: expected {schema['const']!r}")
    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{path}.{name}: missing")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for name in value.keys() - props.keys():
                errors.append(f"{path}.{name}: unknown field")
        for name, sub in props.items():
            if name in value:
                errors += schema_errors(value[name], sub, f"{path}.{name}", root)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: too few items")
        if schema.get("uniqueItems") and any(value[i] == value[j] for i in range(len(value)) for j in range(i)):
            errors.append(f"{path}: duplicate items")
        for i, item in enumerate(value):
            errors += schema_errors(item, schema.get("items", {}), f"{path}[{i}]", root)
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        errors.append(f"{path}: too short")
    if finite:
        for key, test in [("minimum", lambda x: value < x), ("maximum", lambda x: value > x),
                          ("exclusiveMinimum", lambda x: value <= x)]:
            if key in schema and test(schema[key]):
                errors.append(f"{path}: violates {key}={schema[key]}")
    return errors


STAGES = {
    "generation": {"prompt_parse", "model_generate", "generation_total", "candidate_select"},
    "candidate_preparation": {"adapter", "reference_export", "candidate_preparation_total", "artifact_write"},
    "initialization": {"process_start", "model_load", "scene_load", "controller_init", "controller_startup", "warmup", "reset"},
    "control_step": {"dds_state_read", "dds_state_publish", "dds_state_publish_bundle", "dds_command_read",
                     "reference_window", "encoder_infer", "policy_infer", "body_command_publish", "body_pd",
                     "hand_pd", "hand_control", "support_control", "mujoco_step", "mujoco_forward",
                     "physical_evaluator", "grasp_evidence", "loop_compute_total", "pacing_sleep"},
    "episode": {"execution", "episode_total"},
    "postprocess": {"postprocess_total", "video_render", "artifact_write"},
}


def validate_event(event, schema):
    errors = schema_errors(event, schema)
    if errors:
        return errors
    for key in ("event_id", "experiment_id", "config_id", "run_id", "case_id", "hardware_id"):
        if not event[key].strip():
            errors.append(f"{key}: blank string")
    if event["stage"] not in STAGES[event["scope"]]:
        errors.append("stage: invalid for scope")
    if event["clock"] in ("perf_counter_ns", "steady_clock"):
        measured = (event["end_ns"] - event["start_ns"]) / 1e6
        if measured < 0 or abs(measured - event["duration_ms"]) > max(.01, abs(measured) * .02):
            errors.append("duration_ms: inconsistent with monotonic start/end")
    accelerator = event["accelerator"]
    if accelerator:
        count, device_ids = accelerator["device_count"], accelerator["device_ids"]
        if count is None and device_ids:
            errors.append("accelerator: nonempty device_ids require a known device_count")
        elif count is not None and count != len(device_ids):
            errors.append("accelerator: device_count does not match device_ids")
    tr = event["transport"]
    if tr:
        if tr["new_command"] is True and tr["reused_previous_command"] is True:
            errors.append("transport: new and reused are mutually exclusive")
        command_states = [tr[k] for k in ("new_command", "reused_previous_command", "missing_command")]
        if all(value is not None for value in command_states) and sum(value is True for value in command_states) != 1:
            errors.append("transport: exactly one of new/reused/missing must be true when all three are known")
        if tr["missing_command"] is True:
            if any(tr[k] is True for k in ("command_received", "new_command", "reused_previous_command", "stale_command")):
                errors.append("transport: missing command contradicts received flags")
            if tr["command_age_ms"] is not None:
                errors.append("transport: missing command must have null age")
        if any(tr[k] is True for k in ("new_command", "reused_previous_command", "stale_command")) and tr["command_received"] is not True:
            errors.append("transport: command flags require command_received=true")
        age, threshold, stale = (tr[k] for k in ("command_age_ms", "stale_threshold_ms", "stale_command"))
        if stale is not None and (age is None or threshold is None or stale != (age > threshold)):
            errors.append("transport: stale requires age/threshold and must equal age > threshold")
    return errors


def load_events(paths, schema, allow_empty=False):
    events, ids = [], set()
    runs, slots, trial_ids = {}, set(), {}
    for path in paths:
        with Path(path).open(encoding="utf-8-sig") as stream:
            for line_no, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
                    errors = validate_event(event, schema)
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"{path}:{line_no}: {exc}") from exc
                if errors:
                    raise ValueError(f"{path}:{line_no}: {'; '.join(errors)}")
                if event["event_id"] in ids:
                    raise ValueError(f"Duplicate event_id: {event['event_id']}")
                ids.add(event["event_id"])
                identity = tuple(event[k] for k in ("experiment_id", "config_id", "method", "run_type", "case_id", "trial_index"))
                rid = event["run_id"]
                if rid in runs and runs[rid] != identity:
                    raise ValueError(f"Conflicting run identity: {rid}")
                if identity in trial_ids and trial_ids[identity] != rid:
                    raise ValueError("Duplicate trial identity under different run IDs; retries need separate trial_index")
                trial_ids[identity] = rid
                runs[rid] = identity
                if event["scope"] == "control_step":
                    slot = tuple(event[k] for k in ("run_id", "scope", "stage", "clock", "process_id", "thread_id", "frame_index"))
                    if slot in slots:
                        raise ValueError(f"Duplicate control-step sample: {slot}")
                    slots.add(slot)
                events.append(event)
    if not events and not allow_empty:
        raise ValueError("No profiling events")
    return events


def stats(values):
    values = sorted(values)
    if not values:
        return {"count": 0, "mean": None, "p50": None, "p95": None, "p99": None, "min": None, "max": None}
    return {"count": len(values), "mean": statistics.mean(values), "p50": values[math.ceil(.5*len(values))-1],
            "p95": values[math.ceil(.95*len(values))-1], "p99": values[math.ceil(.99*len(values))-1],
            "min": values[0], "max": values[-1]}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def conditions(e):
    keys = ("experiment_id", "config_id", "method", "run_type", "case_id", "scope", "stage", "clock",
            "hardware_id", "device", "synchronized", "profile_overhead_included", "deadline_ms")
    out = {k: e[k] for k in keys}
    a = e["accelerator"]
    out["accelerator_setup"] = None if a is None else {k: v for k, v in a.items() if k not in ("peak_memory_mb", "utilization_percent")}
    t = e["transport"]
    out["transport_setup"] = None if t is None else {k: t[k] for k in ("kind", "topic", "direction", "stale_threshold_ms")}
    return out


def check_manifest(events, manifest):
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "t9_profile_manifest_v0.3" or not isinstance(manifest.get("runs"), list) or not manifest["runs"]:
        raise ValueError("Manifest requires schema_version=t9_profile_manifest_v0.3 and nonempty runs")
    by_run = defaultdict(list)
    for e in events:
        by_run[e["run_id"]].append(e)
    seen, results, identities = set(), [], set()
    for run in manifest["runs"]:
        keys = ("run_id", "experiment_id", "config_id", "method", "run_type", "case_id", "trial_index", "status", "failure_reason", "requirements")
        if not isinstance(run, dict) or any(k not in run for k in keys):
            raise ValueError("Manifest run missing identity/status/failure_reason/requirements")
        rid = run["run_id"]
        if not isinstance(rid, str) or not rid.strip() or rid in seen:
            raise ValueError("Invalid or duplicate manifest run_id")
        if run["method"] not in ("ardy", "kimodo") or run["run_type"] not in ("not_final_smoke", "pilot", "formal"):
            raise ValueError(f"Invalid manifest method/run_type: {rid}")
        for k in ("experiment_id", "config_id", "case_id"):
            if not isinstance(run[k], str) or not run[k].strip():
                raise ValueError(f"Invalid manifest {k}: {rid}")
        if type(run["trial_index"]) is not int or run["trial_index"] < 0:
            raise ValueError(f"Invalid manifest trial_index: {rid}")
        identity = tuple(run[k] for k in ("experiment_id", "config_id", "method", "run_type", "case_id", "trial_index"))
        if identity in identities:
            raise ValueError("Duplicate planned trial identity; retries need separate trial_index")
        identities.add(identity); seen.add(rid)
        if run["status"] not in ("completed", "failed", "timeout", "not_started"):
            raise ValueError(f"Invalid run status: {rid}")
        if run["status"] == "completed":
            if run["failure_reason"] is not None:
                raise ValueError(f"Completed run must have failure_reason=null: {rid}")
        elif not isinstance(run["failure_reason"], str) or not run["failure_reason"].strip():
            raise ValueError(f"Failure/absence needs a reason: {rid}")
        if not isinstance(run["requirements"], list) or (run["status"] == "completed" and not run["requirements"]):
            raise ValueError(f"Completed run requires explicit coverage requirements: {rid}")
        items = by_run.get(rid, [])
        problems = []
        if run["status"] == "not_started" and items:
            problems.append("not_started run has events")
        for e in items:
            if any(e[k] != run[k] for k in keys[:7]):
                problems.append("event/manifest identity mismatch"); break
        requirement_ids = set()
        for req in run["requirements"]:
            if not isinstance(req, dict) or not {"scope", "stage", "clock", "expected_count"} <= req.keys():
                raise ValueError(f"Invalid coverage requirement: {rid}")
            if req["scope"] not in STAGES or req["stage"] not in STAGES[req["scope"]] or req["clock"] not in ("perf_counter_ns", "steady_clock", "cuda_event", "musa_event"):
                raise ValueError(f"Invalid requirement scope/stage/clock: {rid}")
            requirement_id = tuple(req[k] for k in ("scope", "stage", "clock"))
            if requirement_id in requirement_ids:
                raise ValueError(f"Duplicate coverage requirement: {rid} {requirement_id}")
            requirement_ids.add(requirement_id)
            if type(req["expected_count"]) is not int or req["expected_count"] < 0:
                raise ValueError("expected_count must be nonnegative integer")
            selected = [e for e in items if all(e[k] == req[k] for k in ("scope", "stage", "clock"))]
            if len(selected) != req["expected_count"]:
                problems.append(f"{req['scope']}/{req['stage']}: expected {req['expected_count']}, got {len(selected)}")
            if "frame_start" in req or "frame_stride" in req:
                start, stride = req.get("frame_start", 0), req.get("frame_stride", 1)
                if type(start) is not int or start < 0 or type(stride) is not int or stride <= 0:
                    raise ValueError("Invalid frame_start/frame_stride")
                expected = [start + i*stride for i in range(req["expected_count"])]
                frames = [e["frame_index"] for e in selected]
                if any(x is None for x in frames) or sorted(frames) != expected:
                    problems.append(f"{req['stage']}: frame coverage mismatch")
        results.append({k: run[k] for k in keys[:9]} | {"event_count": len(items), "coverage_ok": not problems, "problems": problems})
    extra = set(by_run) - seen
    if extra:
        raise ValueError(f"Unplanned runs: {sorted(extra)}")
    return results


def summarize(events, coverage=None):
    buckets = defaultdict(list)
    run_status = {r["run_id"]: (r["status"], r["coverage_ok"]) for r in (coverage or [])}
    for e in events:
        condition = conditions(e)
        status, coverage_ok = run_status.get(e["run_id"], ("unknown", None))
        condition.update(run_status=status, coverage_ok=coverage_ok)
        buckets[(e["run_id"], canonical(condition))].append(e)
    groups = []
    condition_runs = defaultdict(list)
    for (rid, condition), items in sorted(buckets.items()):
        s = stats([e["duration_ms"] for e in items])
        row = json.loads(condition) | {"run_id": rid, "trial_index": items[0]["trial_index"]}
        row.update({("event_count" if k == "count" else f"{k}_ms"): v for k, v in s.items()})
        deadline = items[0]["deadline_ms"]
        misses = sum(e["duration_ms"] > deadline for e in items) if deadline is not None else None
        row.update(deadline_samples=len(items) if deadline is not None else 0, deadline_misses=misses,
                   deadline_miss_rate=misses/len(items) if misses is not None else None)
        for flag in ("new_command", "reused_previous_command", "missing_command", "stale_command"):
            values = [(e["transport"] or {}).get(flag) for e in items]
            row[flag + "_known_samples"] = sum(v is not None for v in values)
            row[flag + "_true_samples"] = sum(v is True for v in values)
        for field in ("command_age_ms", "command_interval_ms"):
            # interval is summarized only on a read that observes a new arrival.
            vals = [(e["transport"] or {}).get(field) for e in items
                    if field != "command_interval_ms" or (e["transport"] or {}).get("new_command") is True]
            row[field + "_stats"] = stats([v for v in vals if v is not None])
        for field in ("peak_memory_mb", "utilization_percent"):
            vals = [(e["accelerator"] or {}).get(field) for e in items]
            row[field + "_recorded_stats"] = stats([v for v in vals if v is not None])
        groups.append(row)
        condition_runs[condition].append(s["mean"])
    condition_summary = [json.loads(k) | {"run_mean_ms_stats": stats(v)} for k, v in sorted(condition_runs.items())]
    warnings = ["Event percentiles describe samples within runs, not independent trials.",
                "Condition summaries give equal weight to each run mean; no success rate or ranking is inferred.",
                "Nested stages overlap: do not sum all durations. Resource summaries describe recorded values, not time-weighted GPU utilization."]
    if coverage is None:
        warnings.append("No manifest: planned runs and stage/frame completeness are UNVERIFIED.")
    if any(e["profile_overhead_included"] for e in events):
        warnings.append("Some groups include profiling overhead; do not compare against excluded-overhead groups.")
    if any(e["accelerator"] and (e["accelerator"]["shared_device"] is not False or e["accelerator"]["execution_provider"] is None) for e in events):
        warnings.append("Some accelerator sharing/provider facts are shared or unknown; formal comparability is unverified.")
    if any(e["stage"] == "dds_command_read" and any(e["transport"][k] is None for k in ("new_command", "missing_command", "stale_command")) for e in events):
        warnings.append("Some DDS observations are unknown; zero true samples must not be read as zero failures.")
    return {"summary_schema_version": "t9_profile_summary_v0.3", "event_count": len(events),
            "coverage_status": "unverified" if coverage is None else "pass" if all(r["coverage_ok"] for r in coverage) else "fail",
            "runs": coverage, "groups": groups, "condition_groups": condition_summary, "warnings": warnings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", type=Path, nargs="+")
    parser.add_argument("--schema", type=Path, default=Path(__file__).with_name("profiling_schema.json"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--run-type", choices=["not_final_smoke", "pilot", "formal"])
    parser.add_argument("--experiment-id")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--csv-out", type=Path)
    args = parser.parse_args(argv)
    try:
        schema = read_json(args.schema)
        all_events = load_events(args.events, schema, allow_empty=bool(args.manifest))
        def selected(e):
            return (args.run_type is None or e["run_type"] == args.run_type) and (args.experiment_id is None or e["experiment_id"] == args.experiment_id)
        events = [e for e in all_events if selected(e)]
        manifest = read_json(args.manifest) if args.manifest else None
        coverage = check_manifest(all_events, manifest) if manifest else None
        if coverage is not None:
            coverage = [r for r in coverage if selected(r)]
        if not events and not coverage:
            raise ValueError("No events/planned runs match filters")
        if any(e["run_type"] == "formal" for e in events) and manifest is None:
            raise ValueError("Formal summaries require --manifest; completeness must be explicit")
        report = summarize(events, coverage)
        report["filters"] = {"run_type": args.run_type, "experiment_id": args.experiment_id}
        report["excluded_event_count"] = len(all_events) - len(events)
        inputs = {p.resolve() for p in args.events + [args.schema] + ([args.manifest] if args.manifest else [])}
        outputs = [p.resolve() for p in (args.json_out, args.csv_out) if p]
        if len(set(outputs)) != len(outputs) or any(p in inputs or p.exists() for p in outputs):
            raise ValueError("Output paths must be distinct, new, and not overwrite inputs")
        rendered = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        if args.csv_out:
            args.csv_out.parent.mkdir(parents=True, exist_ok=True)
            rows = report["groups"]
            fields = list(rows[0]) if rows else ["run_id", "event_count"]
            with args.csv_out.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fields); writer.writeheader()
                for row in rows:
                    writer.writerow({k: canonical(v) if isinstance(v, (dict, list)) else v for k, v in row.items()})
        return 2 if report["coverage_status"] == "fail" else 0
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
