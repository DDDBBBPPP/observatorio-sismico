import asyncio
import os
import socket
import sys

from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError


BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.environ.get("KAFKA_TEST_TOPIC", "observatorio-test")
PARTITIONS = int(os.environ.get("KAFKA_TEST_PARTITIONS", "1"))
REPLICATION_FACTOR = int(os.environ.get("KAFKA_TEST_REPLICATION_FACTOR", "1"))


async def check() -> None:
    command_line = open("/proc/1/cmdline", encoding="utf-8").read().replace("\x00", " ")
    if "main.py" not in command_line or "serve" not in command_line:
        raise RuntimeError("el proceso persistente producer no está ejecutándose")
    host, _, port = BOOTSTRAP.rpartition(":")
    if not host or not port:
        raise RuntimeError("KAFKA_BOOTSTRAP_SERVERS no tiene formato host:puerto")
    await asyncio.get_running_loop().run_in_executor(
        None, lambda: socket.getaddrinfo(host, int(port), type=socket.SOCK_STREAM)
    )

    admin = AIOKafkaAdminClient(bootstrap_servers=BOOTSTRAP, client_id="producer-healthcheck")
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


if __name__ == "__main__":
    try:
        asyncio.run(check())
    except Exception as exc:
        print(f"producer unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1)
