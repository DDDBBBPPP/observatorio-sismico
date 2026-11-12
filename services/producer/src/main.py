import asyncio
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

from aiokafka import AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError

from event_model import build_test_event

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.environ.get("KAFKA_TEST_TOPIC", "observatorio-test")
PARTITIONS = int(os.environ.get("KAFKA_TEST_PARTITIONS", "1"))
REPLICATION_FACTOR = int(os.environ.get("KAFKA_TEST_REPLICATION_FACTOR", "1"))
PUBLISH_TIMEOUT_SECONDS = float(os.environ.get("KAFKA_PUBLISH_TIMEOUT_SECONDS", "10"))


async def ensure_topic() -> None:
    host, _, port = BOOTSTRAP.rpartition(":")
    await asyncio.get_running_loop().run_in_executor(
        None, lambda: socket.getaddrinfo(host, int(port), type=socket.SOCK_STREAM)
    )
    admin = AIOKafkaAdminClient(bootstrap_servers=BOOTSTRAP, client_id="producer")
    await admin.start()
    try:
        try:
            await admin.create_topics(
                [NewTopic(TOPIC, num_partitions=PARTITIONS, replication_factor=REPLICATION_FACTOR)]
            )
        except TopicAlreadyExistsError:
            pass
        topics = await admin.describe_topics([TOPIC])
        topic = topics[0] if topics else None
        if topic is None or len(topic["partitions"]) != PARTITIONS:
            raise RuntimeError("el topic no tiene exactamente una partición")
        if any(
            len(partition["replicas"]) != REPLICATION_FACTOR
            for partition in topic["partitions"]
        ):
            raise RuntimeError("el topic no tiene exactamente una réplica")
    finally:
        await admin.close()


async def serve() -> None:
    await ensure_topic()
    print(f'{{"state":"ready","topic":"{TOPIC}"}}', flush=True)
    while True:
        await asyncio.sleep(30)


async def publish_test() -> int:
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
    if len(sys.argv) != 2 or sys.argv[1] not in {"serve", "publish-test"}:
        raise SystemExit("Uso: python /app/src/main.py serve|publish-test")
    if sys.argv[1] == "serve":
        asyncio.run(serve())
    else:
        raise SystemExit(asyncio.run(publish_test()))


if __name__ == "__main__":
    main()
