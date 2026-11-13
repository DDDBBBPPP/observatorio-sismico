import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from aiokafka import AIOKafkaConsumer


BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.environ.get("KAFKA_TEST_TOPIC", "observatorio-test")


async def serve() -> None:
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        group_id="observatorio-consumer",
        enable_auto_commit=True,
    )
    await consumer.start()
    try:
        print(f'{{"state":"ready","topic":"{TOPIC}"}}', flush=True)
        async for message in consumer:
            try:
                payload = json.loads(message.value.decode("utf-8"))
                if (
                    payload.get("schema") != "observatorio.test-envelope.v1"
                    or payload.get("source") != "synthetic-test"
                    or payload.get("mode") != "test"
                    or not payload.get("run_id")
                ):
                    continue
                run_dir = Path("/evidence") / payload["run_id"]
                run_dir.mkdir(parents=True, exist_ok=True)
                path = run_dir / "consumer.json"
                records = []
                if path.exists():
                    records = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(records, list):
                        records = [records]
                records.append(
                    {
                        "run_id": payload["run_id"],
                        "received_at": datetime.now(timezone.utc).isoformat(),
                        "status": "received",
                        "message": payload,
                    }
                )
                path.write_text(
                    json.dumps(records, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                print(json.dumps(records[-1], ensure_ascii=False), flush=True)
            except (UnicodeDecodeError, json.JSONDecodeError, OSError, TypeError) as exc:
                print(f"consumer failed to record message: {exc}", file=sys.stderr, flush=True)
    finally:
        await consumer.stop()


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] != "serve":
        raise SystemExit("Uso: python /app/src/main.py serve")
    asyncio.run(serve())


if __name__ == "__main__":
    main()
