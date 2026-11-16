import json
from datetime import datetime, timezone
from pathlib import Path

from geography import CountryCatalog
from persistence import connect, ensure_schema, finish_ingestion_run, persist_live_event, persist_quarantine, start_ingestion_run
from validation import validate_live_event


def process_manifest(path: str, max_intervals: int | None = None, run_suffix: str = "") -> dict:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    assert manifest["filters"]["minmagnitude"] == 4
    assert manifest["filters"]["eventtype"] == "earthquake"
    intervals = manifest["intervals"]
    assert len(intervals) == 12 and sum(i["record_count"] for i in intervals) == 18302
    run_id = f"historical-{manifest['year']}-minmag4-earthquake{run_suffix}"
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(hashtext(%s))", ("historical-2025",))
            if not cursor.fetchone()[0]:
                raise RuntimeError("Ya hay un batch histórico en ejecución")
        ensure_schema(connection)
        with connection.cursor() as cursor:
            cursor.execute("SELECT status, records_seen FROM ingestion_run WHERE run_id=%s", (run_id,))
            prior = cursor.fetchone()
            cursor.execute("SELECT count(*) FROM historical_interval_checkpoint WHERE run_id=%s", (run_id,))
            completed_intervals = cursor.fetchone()[0]
            if prior and prior[0] == "completed" and (completed_intervals == len(intervals) or
                (completed_intervals == 0 and prior[1] == 18302)):
                result = {"run_id": run_id, "status": "already_completed", "intervals": len(intervals)}
                print(json.dumps(result), flush=True)
                return result
        start_ingestion_run(connection, run_id, "historical_initial", "historical")
        catalog = CountryCatalog()
        for index, interval in enumerate(intervals[:max_intervals] if max_intervals else intervals, 1):
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM historical_interval_checkpoint WHERE run_id=%s AND interval_start=%s", (run_id, interval["interval_start"]))
                if cursor.fetchone():
                    print(json.dumps({"interval": index, "status": "skipped_checkpoint"}), flush=True)
                    continue
            document = json.loads(Path(interval["path"]).read_text(encoding="utf-8"))
            features = document["payload"].get("features", [])
            if len(features) != interval["record_count"]:
                raise ValueError(f"Recuento original distinto en intervalo {index}")
            metadata = document["metadata"]
            response_id = f"{run_id}-response-{Path(interval['path']).parent.name}"
            accepted = duplicates = quarantined = 0
            try:
                # Store the large original once; per-event upserts below send only {}.
                with connection.cursor() as cursor:
                    cursor.execute("INSERT INTO source_response (response_id,run_id,url,requested_at,received_at,http_status,duration_ms,record_count,payload_jsonb) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (response_id) DO NOTHING", (response_id, run_id, metadata["url"], metadata["requested_at"], metadata["received_at"], metadata["http_status"], metadata["duration_ms"], metadata["record_count"], json.dumps(document["payload"])))
                for feature in features:
                    properties = feature.get("properties") or {}
                    payload = {
                        "schema": "observatorio.event-envelope.v1", "run_id": run_id,
                        "source": "usgs", "mode": "historical", "event": feature,
                        "event_id": feature.get("id"), "updated": properties.get("updated"),
                        "provenance": {
                            "run_id": run_id, "source_response_id": response_id,
                            "load_type": "historical_initial", "url": metadata["url"],
                            "requested_at": metadata["requested_at"], "received_at": metadata["received_at"],
                            "http_status": metadata["http_status"], "duration_ms": metadata["duration_ms"],
                            "record_count": metadata["record_count"], "original": {},
                        },
                    }
                    valid, reason = validate_live_event(feature)
                    if not valid:
                        persist_quarantine(connection, payload, reason, commit=False)
                        quarantined += 1
                        continue
                    coordinates = feature["geometry"]["coordinates"]
                    country = catalog.assign(float(coordinates[0]), float(coordinates[1]))
                    status = persist_live_event(connection, payload, country, commit=False)
                    duplicates += status == "duplicate_version"
                    accepted += status == "accepted"
                with connection.cursor() as cursor:
                    cursor.execute("INSERT INTO historical_interval_checkpoint (run_id,interval_start,record_count,accepted,duplicates,quarantined) VALUES (%s,%s,%s,%s,%s,%s)", (run_id, interval["interval_start"], len(features), accepted, duplicates, quarantined))
                    cursor.execute("UPDATE ingestion_run SET status='running' WHERE run_id=%s", (run_id,))
                connection.commit()
                print(json.dumps({"interval": index, "of": len(intervals), "seen": len(features), "accepted": accepted, "duplicates": duplicates, "quarantined": quarantined, "status": "committed"}), flush=True)
            except Exception:
                connection.rollback()
                raise
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*),coalesce(sum(record_count),0),coalesce(sum(accepted),0),coalesce(sum(duplicates),0),coalesce(sum(quarantined),0) FROM historical_interval_checkpoint WHERE run_id=%s", (run_id,))
            done, seen, accepted, duplicates, quarantined = cursor.fetchone()
        if done == len(intervals):
            finish_ingestion_run(connection, run_id, seen, accepted, quarantined)
        else:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE ingestion_run SET status='partial', records_seen=%s, records_accepted=%s, records_rejected=%s WHERE run_id=%s", (seen, accepted, quarantined, run_id))
            connection.commit()
        result = {"run_id": run_id, "status": "completed" if done == len(intervals) else "partial", "intervals": done, "seen": seen, "accepted": accepted, "duplicates": duplicates, "quarantined": quarantined, "processed_at": datetime.now(timezone.utc).isoformat()}
        print(json.dumps(result), flush=True)
        return result
    finally:
        connection.close()
