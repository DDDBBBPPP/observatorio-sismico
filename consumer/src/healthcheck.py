import asyncio
import os
import sys

from aiokafka import AIOKafkaConsumer


BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.environ.get("KAFKA_TEST_TOPIC", "observatorio-test")


async def check() -> None:
    command_line = open("/proc/1/cmdline", encoding="utf-8").read().replace("\x00", " ")
    if "main.py" not in command_line or "serve" not in command_line:
        raise RuntimeError("el proceso persistente consumer no está ejecutándose")
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        group_id="observatorio-healthcheck",
        request_timeout_ms=5000,
    )
    await consumer.start()
    await consumer.stop()


if __name__ == "__main__":
    try:
        asyncio.run(check())
    except Exception as exc:
        print(f"consumer unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1)
