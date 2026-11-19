"""Bounded Kafka integration: duplicate, newer, older, poison and restart."""
import json
import subprocess
import time
from datetime import datetime, timezone
from uuid import uuid4


TOPIC = "observatorio-usgs-live"
WRITER = """import asyncio,sys;from aiokafka import AIOKafkaProducer
async def run():
 p=AIOKafkaProducer(bootstrap_servers='kafka:9092');await p.start()
 try:
  await p.send_and_wait('observatorio-usgs-live',bytes.fromhex(sys.argv[1]),key=sys.argv[2].encode())
 finally: await p.stop()
asyncio.run(run())"""
READER = """import json,sys;sys.path.insert(0,'/app/src');from persistence import connect
c=connect();cur=c.cursor();cur.execute('SELECT current_updated,mag,is_synthetic FROM event_current WHERE event_id=%s',(sys.argv[1],));current=cur.fetchone();cur.execute('SELECT count(*) FROM event_version WHERE event_id=%s',(sys.argv[1],));versions=cur.fetchone()[0];cur.execute(\"SELECT count(*) FROM quarantine_record WHERE payload_reference LIKE %s\",('observatorio-usgs-live:%',));poison=cur.fetchone()[0];print(json.dumps({'current':current,'versions':versions,'poison':poison}));c.close()"""


def docker(*args: str, timeout: int = 25) -> str:
    return subprocess.run(("docker", "compose", *args), check=True, text=True,
                          capture_output=True, timeout=timeout).stdout.strip()


def state(event_id: str) -> dict:
    raw = docker("exec", "-T", "consumer", "python", "-c", READER, event_id)
    return json.loads(raw.splitlines()[-1])


def wait_for(event_id: str, expected: int, timeout: int = 30) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = state(event_id)
        if current["versions"] == expected:
            return current
        time.sleep(1)
    raise AssertionError(f"Consumer did not reach {expected} versions: {current}")


def main() -> None:
    event_id = "controlled-kafka-" + uuid4().hex
    run_id = "controlled-kafka-run-" + uuid4().hex
    response_id = "controlled-kafka-response-" + uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    before_poison = state(event_id)["poison"]
    def publish(updated: int, mag: float) -> None:
        event = {"type": "Feature", "id": event_id,
                 "properties": {"type": "earthquake", "time": 1794787200000,
                                "updated": updated, "mag": mag, "place": "Control Kafka"},
                 "geometry": {"type": "Point", "coordinates": [0, 0, 10]}}
        message = {"schema": "observatorio.event-envelope.v1", "run_id": run_id,
                   "source": "usgs", "mode": "live", "event": event,
                   "event_id": event_id, "updated": updated,
                   "provenance": {"run_id": run_id, "source_response_id": response_id,
                                  "load_type": "live_feed", "url": "test://kafka",
                                  "requested_at": now, "received_at": now,
                                  "http_status": 200, "duration_ms": 0, "record_count": 4,
                                  "original": {"features": [event]}}}
        docker("exec", "-T", "producer", "python", "-c", WRITER,
               json.dumps(message).encode().hex(), event_id)
    publish(1000, 1.0)
    assert wait_for(event_id, 1)["current"][:2] == [1000, 1.0]
    docker("restart", "consumer", timeout=35)
    publish(3000, 3.0)
    publish(2000, 2.0)
    publish(2000, 2.0)
    current = wait_for(event_id, 3)
    assert current["current"] == [3000, 3.0, True], current
    # Allow the duplicate to pass before checking for a fourth version.
    time.sleep(2)
    assert state(event_id)["versions"] == 3
    docker("exec", "-T", "producer", "python", "-c", WRITER, b"{broken-json".hex(), event_id)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and state(event_id)["poison"] <= before_poison:
        time.sleep(1)
    assert state(event_id)["poison"] == before_poison + 1
    rows = docker("ps", "--format", "json", "consumer")
    assert all(row.get("Health") == "healthy" for row in (json.loads(line) for line in rows.splitlines()))
    print(json.dumps({"event_id": event_id, "versions": 3, "current_updated": 3000,
                      "duplicate": "ignored", "older": "not_current",
                      "poison": "quarantined", "restart": "passed"}))


if __name__ == "__main__":
    main()
