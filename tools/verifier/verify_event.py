import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [record for record in data if isinstance(record, dict)]
    return [data] if isinstance(data, dict) else []


def compare_messages(producer: dict, consumer: dict) -> list[str]:
    differences = []
    expected = producer.get("message")
    actual = consumer.get("message")
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return ["message ausente o no es un objeto"]
    for field in ("schema", "run_id", "source", "mode", "created_at", "event"):
        if expected.get(field) != actual.get(field):
            differences.append(f"{field}: productor={expected.get(field)!r}, consumidor={actual.get(field)!r}")
    expected_event = expected.get("event")
    actual_event = actual.get("event")
    if isinstance(expected_event, dict) and isinstance(actual_event, dict):
        for field in sorted(set(expected_event) | set(actual_event)):
            if expected_event.get(field) != actual_event.get(field):
                differences.append(
                    f"event.{field}: productor={expected_event.get(field)!r}, consumidor={actual_event.get(field)!r}"
                )
    return differences


def verify(args: argparse.Namespace) -> tuple[int, dict]:
    evidence_dir = Path(args.evidence_dir)
    producer_path = evidence_dir / "producer.json"
    producer_records = load_records(producer_path)
    producer = next(
        (record for record in producer_records if record.get("run_id") == args.run_id),
        None,
    )
    result = {
        "run_id": args.run_id,
        "checked_at": datetime.now().astimezone().isoformat(),
        "status": "receive_failed",
    }
    if producer is None or producer.get("status") != "send_confirmed":
        result["reason"] = "evidencia de productor ausente o sin send_confirmed"
        return 1, result
    started_at = parse_timestamp(args.started_at)
    consumer_path = Path(args.consumer_json) if args.consumer_json else evidence_dir / "consumer.json"
    deadline = time.monotonic() + args.timeout_seconds
    consumer = None
    while time.monotonic() <= deadline:
        candidates = [
            record
            for record in load_records(consumer_path)
            if record.get("run_id") == args.run_id
            and record.get("status") == "received"
            and parse_timestamp(record["received_at"]) >= started_at
        ]
        if len(candidates) == 1:
            consumer = candidates[0]
            break
        if len(candidates) > 1:
            result["reason"] = "hay más de una evidencia del consumidor para el run_id"
            return 1, result
        time.sleep(0.25)
    if consumer is None:
        result["reason"] = "evidencia del consumidor ausente, antigua o fuera de plazo"
        return 1, result
    differences = compare_messages(producer, consumer)
    result["producer"] = producer
    result["consumer"] = consumer
    if differences:
        result["differences"] = differences
        return 1, result
    result["status"] = "receive_confirmed"
    return 0, result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--consumer-json")
    parser.add_argument("--timeout-seconds", type=float, default=30)
    args = parser.parse_args()
    try:
        code, result = verify(args)
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        code, result = 1, {"run_id": args.run_id, "status": "receive_failed", "reason": str(exc)}
    output = Path(args.evidence_dir) / "verification.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
