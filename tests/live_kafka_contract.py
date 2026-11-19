"""Read recent live Kafka records and verify actual producer key/provenance."""
import asyncio
import json
import sys

from aiokafka import AIOKafkaConsumer, TopicPartition

sys.path.insert(0, "/app/src")
from message_contract import original_for  # noqa: E402


async def main():
    consumer = AIOKafkaConsumer(bootstrap_servers="kafka:9092", enable_auto_commit=False)
    await consumer.start()
    try:
        partition = TopicPartition("observatorio-usgs-live", 0)
        consumer.assign([partition])
        await consumer.seek_to_end(partition)
        end = await consumer.position(partition)
        consumer.seek(partition, max(0, end - 50))
        messages = []
        for _ in range(20):
            batches = await consumer.getmany(timeout_ms=1000, max_records=100)
            messages.extend(batches.get(partition, []))
            if await consumer.position(partition) >= end:
                break
        for message in reversed(messages):
            try:
                payload = json.loads(message.value)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if payload.get("mode") == "live" and payload.get("source") == "usgs" and not payload.get("event_id", "").startswith("controlled-") and "original_reference" in payload.get("provenance", {}):
                assert message.key == payload["event_id"].encode(), "Kafka key is not event_id"
                assert "original" not in payload["provenance"], "Full response repeated in Kafka"
                original_for(payload)
                print(json.dumps({"event_id": payload["event_id"], "offset": message.offset,
                                  "key": message.key.decode(), "original_sha256": payload["provenance"]["original_sha256"]}))
                return
        raise AssertionError(f"No recent compact live record found; end={end}, read={len(messages)}, last={[(m.offset, m.key, list(json.loads(m.value).get('provenance', {}))) for m in messages[-3:]]}")
    finally:
        await consumer.stop()


asyncio.run(main())
