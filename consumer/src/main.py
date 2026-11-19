import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from aiokafka import AIOKafkaConsumer

from persistence import connect, ensure_schema, persist_bad_message, persist_live_event, persist_replay_event, prune_live_response_payloads
from geography import CountryCatalog
from message_contract import original_for, validate_envelope
from batch import process_manifest


BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.environ.get("KAFKA_TEST_TOPIC", "observatorio-test")
LIVE_TOPIC = os.environ.get("KAFKA_LIVE_TOPIC", "observatorio-usgs-live")
REPLAY_TOPIC = os.environ.get("KAFKA_REPLAY_TOPIC", "observatorio-usgs-replay")


async def serve() -> None:
    consumer = AIOKafkaConsumer(
        TOPIC,
        LIVE_TOPIC,
        REPLAY_TOPIC,
        bootstrap_servers=BOOTSTRAP,
        group_id="observatorio-consumer",
        enable_auto_commit=False,
    )
    connection = connect()
    ensure_schema(connection)
    catalog = CountryCatalog()
    last_prune = 0.0
    await consumer.start()
    try:
        print(f'{{"state":"ready","topic":"{TOPIC}"}}', flush=True)
        async for message in consumer:
            try:
                if time.monotonic() - last_prune > 86400:
                    prune_live_response_payloads(connection)
                    last_prune = time.monotonic()
                try:
                    payload = json.loads(message.value.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    persist_bad_message(connection, message.topic, message.partition, message.offset, "invalid_json", message.value)
                    await consumer.commit()
                    continue
                if isinstance(payload, dict) and (
                    payload.get("schema") != "observatorio.test-envelope.v1"
                    or payload.get("source") != "synthetic-test"
                    or payload.get("mode") != "test"
                    or not payload.get("run_id")
                ):
                    if message.topic not in {LIVE_TOPIC, REPLAY_TOPIC}:
                        await consumer.commit()
                        continue
                    reason = validate_envelope(payload, message.topic, LIVE_TOPIC, REPLAY_TOPIC)
                    if reason:
                        persist_bad_message(connection, message.topic, message.partition, message.offset, reason, message.value)
                        await consumer.commit()
                        print(
                            json.dumps(
                                {
                                    "run_id": payload.get("run_id") if isinstance(payload, dict) else None,
                                    "event_id": payload.get("event_id") if isinstance(payload, dict) else None,
                                    "status": "quarantined",
                                    "reason": reason,
                                }
                            ),
                            flush=True,
                        )
                        continue
                    if message.topic == LIVE_TOPIC:
                        try:
                            payload["provenance"]["original"] = original_for(payload)
                        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                            persist_bad_message(connection, message.topic, message.partition, message.offset, f"original_unverifiable:{type(exc).__name__}", message.value)
                            await consumer.commit()
                            continue
                    coordinates = payload["event"]["geometry"]["coordinates"]
                    country = catalog.assign(float(coordinates[0]), float(coordinates[1]))
                    if message.topic == REPLAY_TOPIC and payload.get("mode") == "replay":
                        status = persist_replay_event(connection, payload, country)
                    elif message.topic == LIVE_TOPIC and payload.get("mode") == "live":
                        status = persist_live_event(connection, payload, country)
                    else:
                        print(json.dumps({"status": "topic_mode_mismatch", "topic": message.topic}), file=sys.stderr, flush=True)
                        await consumer.commit()
                        continue
                    print(
                        json.dumps(
                            {
                                "run_id": payload["run_id"],
                                "event_id": payload["event_id"],
                                "status": status,
                            }
                        ),
                        flush=True,
                    )
                    await consumer.commit()
                    continue
                run_dir = Path("/evidence") / payload["run_id"]
                run_dir.mkdir(parents=True, exist_ok=True)
                path = run_dir / "consumer.json"
                records = []
                if path.exists():
                    records = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(records, list):
                        records = [records]
                records.append({"run_id": payload["run_id"], "received_at": datetime.now(timezone.utc).isoformat(), "status": "received", "message": payload})
                path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                await consumer.commit()
                print(json.dumps(records[-1], ensure_ascii=False), flush=True)
            except Exception as exc:
                connection.rollback()
                print(f"consumer failed to record message at {message.topic}:{message.partition}:{message.offset}: {exc}", file=sys.stderr, flush=True)
                raise
    finally:
        connection.close()
        await consumer.stop()


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "process-historical":
        if len(sys.argv) < 3:
            raise SystemExit("Uso: process-historical MANIFEST [--max-intervals N] [--run-suffix SUFFIX]")
        from argparse import ArgumentParser
        parser = ArgumentParser()
        parser.add_argument("manifest")
        parser.add_argument("--max-intervals", type=int)
        parser.add_argument("--run-suffix", default="")
        args = parser.parse_args(sys.argv[2:])
        process_manifest(args.manifest, args.max_intervals, args.run_suffix)
        return
    if len(sys.argv) != 2 or sys.argv[1] != "serve":
        raise SystemExit("Uso: python /app/src/main.py serve|process-historical <manifest>")
    asyncio.run(serve())


if __name__ == "__main__":
    main()
