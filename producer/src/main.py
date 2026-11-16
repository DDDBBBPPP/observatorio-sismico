import asyncio
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from aiokafka import AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError

from event_model import build_live_event, build_test_event
from ingestion_state import IngestionState
from live_ingest import new_earthquakes
from historical_loader import load_year
from topic_config import live_topic, replay_topic, validated_topic_shape
from usgs_client import fetch_feed, save_latest_live_fetch, save_original

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.environ.get("KAFKA_TEST_TOPIC", "observatorio-test")
LIVE_TOPIC = live_topic()
REPLAY_TOPIC = replay_topic()
PUBLISH_TIMEOUT_SECONDS = float(os.environ.get("KAFKA_PUBLISH_TIMEOUT_SECONDS", "10"))
POLL_INTERVAL_SECONDS = max(30, int(os.environ.get("USGS_POLL_INTERVAL_SECONDS", "60")))


async def ensure_topic(topic_name: str) -> None:
    partitions, replication_factor = validated_topic_shape()
    host, _, port = BOOTSTRAP.rpartition(":")
    await asyncio.get_running_loop().run_in_executor(
        None, lambda: socket.getaddrinfo(host, int(port), type=socket.SOCK_STREAM)
    )
    admin = AIOKafkaAdminClient(bootstrap_servers=BOOTSTRAP, client_id="producer")
    await admin.start()
    try:
        try:
            await admin.create_topics(
                [NewTopic(topic_name, num_partitions=partitions, replication_factor=replication_factor)]
            )
        except TopicAlreadyExistsError:
            pass
        topics = await admin.describe_topics([topic_name])
        topic = topics[0] if topics else None
        if topic is None or len(topic["partitions"]) != partitions:
            raise RuntimeError("el topic no tiene exactamente una partición")
        if any(
            len(partition["replicas"]) != replication_factor
            for partition in topic["partitions"]
        ):
            raise RuntimeError("el topic no tiene exactamente una réplica")
    finally:
        await admin.close()


async def serve() -> None:
    await ensure_topic(TOPIC)
    await ensure_topic(LIVE_TOPIC)
    await ensure_topic(REPLAY_TOPIC)
    print(f'{{"state":"ready","topic":"{TOPIC}","live_topic":"{LIVE_TOPIC}","replay_topic":"{REPLAY_TOPIC}"}}', flush=True)
    while True:
        try:
            await ingest_live()
        except Exception as exc:
            failure = {"status": "live_fetch_failed", "at": datetime.now(timezone.utc).isoformat(), "error": str(exc)}
            print(json.dumps(failure), file=sys.stderr, flush=True)
            error_path = Path("/evidence/002-ingesta-usgs-persistencia/live-errors.jsonl")
            error_path.parent.mkdir(parents=True, exist_ok=True)
            with error_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(failure, ensure_ascii=False) + "\n")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def replay_historical(path: str, limit: int = 10, delay_seconds: float = 0.25) -> int:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await asyncio.wait_for(producer.start(), timeout=PUBLISH_TIMEOUT_SECONDS)
    published = 0
    try:
        for interval in manifest["intervals"]:
            if published >= limit:
                break
            document = json.loads(Path(interval["path"]).read_text(encoding="utf-8"))
            for feature in document["payload"].get("features", []):
                if published >= limit:
                    break
                properties = feature.get("properties") or {}
                if properties.get("type") != "earthquake" or not isinstance(properties.get("updated"), int):
                    continue
                message = build_live_event(
                    feature,
                    f"replay-{manifest['year']}",
                    f"replay-response-{Path(interval['path']).parent.name}",
                )
                message["mode"] = "replay"
                message["replay_at"] = datetime.now(timezone.utc).isoformat()
                message["original_event_time"] = properties.get("time")
                message["provenance"].update(
                    {
                        "load_type": "historical_replay",
                        "url": document["metadata"]["url"],
                        "requested_at": document["metadata"]["requested_at"],
                        "received_at": document["metadata"]["received_at"],
                        "http_status": document["metadata"]["http_status"],
                        "duration_ms": document["metadata"]["duration_ms"],
                        "record_count": document["metadata"]["record_count"],
                        "original": feature,
                        "original_reference": interval["path"],
                    }
                )
                await asyncio.wait_for(
                    producer.send_and_wait(
                        REPLAY_TOPIC,
                        json.dumps(message, ensure_ascii=False).encode("utf-8"),
                        key=feature["id"].encode("utf-8"),
                    ),
                    timeout=PUBLISH_TIMEOUT_SECONDS,
                )
                published += 1
                await asyncio.sleep(delay_seconds)
    finally:
        await producer.stop()
    print(json.dumps({"status": "replay_send_confirmed", "topic": REPLAY_TOPIC, "published": published}))
    return 0


async def ingest_live() -> int:
    payload, metadata = fetch_feed()
    run_id = f"run-{uuid4().hex}"
    response_id = f"response-{uuid4().hex}"
    metadata["original"] = payload
    original_path = save_original(payload, metadata, run_id)
    save_latest_live_fetch(metadata, run_id)
    state = IngestionState(original_path.parent.parent / "state.json")
    features, excluded = new_earthquakes(payload, state)
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await asyncio.wait_for(producer.start(), timeout=PUBLISH_TIMEOUT_SECONDS)
    try:
        for feature in features:
            message = build_live_event(feature, run_id, response_id)
            message["provenance"].update(
                {
                    "url": metadata["url"],
                    "requested_at": metadata["requested_at"],
                    "received_at": metadata["received_at"],
                    "http_status": metadata["http_status"],
                    "duration_ms": metadata["duration_ms"],
                    "record_count": metadata["record_count"],
                    "original": payload,
                }
            )
            await asyncio.wait_for(
                producer.send_and_wait(
                    LIVE_TOPIC,
                    json.dumps(message, ensure_ascii=False).encode("utf-8"),
                ),
                timeout=PUBLISH_TIMEOUT_SECONDS,
            )
            state.record_version(feature["id"], feature["properties"]["updated"])
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "response_id": response_id,
                    "status": "send_confirmed",
                    "topic": LIVE_TOPIC,
                    "published": len(features),
                    "excluded": excluded,
                    "original": str(original_path),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        return 0
    finally:
        await producer.stop()


async def publish_test() -> int:
    validated_topic_shape()
    message = build_test_event()
    evidence_dir = Path("/evidence") / message["run_id"]
    evidence_dir.mkdir(parents=True, exist_ok=False)
    producer_evidence = {
        "run_id": message["run_id"],
        "event_id": message["event"]["event_id"],
        "status": "send_attempted",
        "attempted_at": datetime.now(timezone.utc).isoformat(),
        "message": message,
    }
    evidence_path = evidence_dir / "producer.json"
    evidence_path.write_text(json.dumps(producer_evidence, ensure_ascii=False, indent=2) + "\n")
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    try:
        await asyncio.wait_for(producer.start(), timeout=PUBLISH_TIMEOUT_SECONDS)
        metadata = await asyncio.wait_for(
            producer.send_and_wait(
                TOPIC,
                json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            ),
            timeout=PUBLISH_TIMEOUT_SECONDS,
        )
        producer_evidence.update(
            {
                "status": "send_confirmed",
                "confirmed_at": datetime.now(timezone.utc).isoformat(),
                "kafka": {
                    "topic": metadata.topic,
                    "partition": metadata.partition,
                    "offset": metadata.offset,
                },
            }
        )
        evidence_path.write_text(json.dumps(producer_evidence, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(producer_evidence, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        producer_evidence.update(
            {
                "status": "send_failed",
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            }
        )
        evidence_path.write_text(json.dumps(producer_evidence, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(producer_evidence, ensure_ascii=False), file=sys.stderr, flush=True)
        return 1
    finally:
        await producer.stop()


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {
        "serve", "publish-test", "ingest-live", "load-historical", "replay-historical"
    }:
        raise SystemExit("Uso: python /app/src/main.py serve|publish-test|ingest-live|load-historical [year]|replay-historical <manifest>")
    validated_topic_shape()
    if sys.argv[1] == "serve":
        asyncio.run(serve())
    elif sys.argv[1] == "publish-test":
        raise SystemExit(asyncio.run(publish_test()))
    elif sys.argv[1] == "ingest-live":
        raise SystemExit(asyncio.run(ingest_live()))
    elif sys.argv[1] == "replay-historical":
        from argparse import ArgumentParser
        parser = ArgumentParser()
        parser.add_argument("manifest")
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--delay-seconds", type=float, default=0.25)
        args = parser.parse_args(sys.argv[2:])
        if args.limit < 1 or not 0 <= args.delay_seconds <= 10:
            raise SystemExit("limit debe ser positivo y delay-seconds entre 0 y 10")
        raise SystemExit(asyncio.run(replay_historical(args.manifest, args.limit, args.delay_seconds)))
    else:
        year = int(sys.argv[2]) if len(sys.argv) == 3 else 2025
        print(json.dumps(load_year(year), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
