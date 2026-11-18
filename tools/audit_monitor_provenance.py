"""Read-only audit of one preserved USGS response against SQL and paged API."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/002-ingesta-usgs-persistencia"
RUN = "run-69a12a1cd6594e70abf0483afaf3bcc2"
SAMPLE = "2026-11-18T17:23:04.112254+00:00"
START = "2026-11-17T17:23:04.112254+00:00"
END = SAMPLE

DB_CODE = r'''
import json, sys
sys.path.insert(0, '/app/src')
from persistence import connect
from datetime import datetime
start_ms, end_ms, sample, run_id = sys.argv[1:]
start_ms, end_ms = int(start_ms), int(end_ms)
conn = connect()
try:
    with conn.cursor() as cur:
        cur.execute('SET TRANSACTION READ ONLY')
        cur.execute("SET LOCAL statement_timeout = '5s'")
        cur.execute("""SELECT r.run_id,r.started_at,r.finished_at,r.records_seen,r.records_accepted,
                       r.records_rejected,s.response_id,s.url,s.requested_at,s.received_at,
                       s.http_status,s.duration_ms,s.record_count
                       FROM ingestion_run r LEFT JOIN source_response s ON s.run_id=r.run_id
                       WHERE r.run_id=%s ORDER BY s.received_at LIMIT 5""", (run_id,))
        source_run = cur.fetchall()
        cur.execute("""SELECT v.event_id,v.updated,v.event_time,v.ingested_at,v.run_id,
                       v.source_response_id,s.received_at
                       FROM event_version v LEFT JOIN source_response s
                         ON s.response_id=v.source_response_id
                       WHERE v.mode='live' AND v.load_type='live_feed'
                         AND v.is_synthetic=FALSE AND v.event_time >= %s AND v.event_time < %s
                       ORDER BY v.event_id,v.updated""", (start_ms,end_ms))
        versions = cur.fetchall()
        cur.execute("""SELECT event_id,updated,event_time,ingested_at
                       FROM event_version WHERE run_id=%s ORDER BY event_id,updated""", (run_id,))
        run_versions = cur.fetchall()
        cur.execute("""SELECT c.event_id,c.current_updated,c.event_time,v.run_id,
                       v.source_response_id,s.received_at
                       FROM event_current c JOIN event_version v
                         ON v.event_version_id=c.event_version_id
                       LEFT JOIN source_response s ON s.response_id=v.source_response_id
                       WHERE c.is_synthetic=FALSE AND c.event_time >= %s AND c.event_time < %s
                       ORDER BY c.event_id""", (start_ms,end_ms))
        current = cur.fetchall()
        cur.execute("""SELECT event_id,updated,event_time,run_id,source_response_id,ingested_at
                       FROM (SELECT DISTINCT ON (event_id) event_id,updated,event_time,run_id,
                                    source_response_id,ingested_at
                             FROM event_version
                             WHERE mode='live' AND load_type='live_feed' AND is_synthetic=FALSE
                               AND ingested_at <= %s
                             ORDER BY event_id,updated DESC,ingested_at DESC) q
                       WHERE event_time >= %s AND event_time < %s ORDER BY event_id""",
                    (sample,start_ms,end_ms))
        asof = cur.fetchall()
        cur.execute("""SELECT i.relname,pg_relation_size(i.oid),pg_get_indexdef(i.oid),
                       ix.indisunique,coalesce(st.idx_scan,0)
                       FROM pg_class t JOIN pg_index ix ON ix.indrelid=t.oid
                       JOIN pg_class i ON i.oid=ix.indexrelid
                       LEFT JOIN pg_stat_user_indexes st ON st.indexrelid=i.oid
                       WHERE t.relname IN ('event_version','event_current','source_response',
                           'ingestion_run','quarantine_record','historical_interval_checkpoint',
                           'replay_event_version','replay_event_current')
                       AND t.relnamespace=(SELECT oid FROM pg_namespace WHERE nspname=current_schema())
                       ORDER BY t.relname,i.relname""")
        indexes = cur.fetchall()
        cur.execute("""SELECT conrelid::regclass::text,conname,contype,pg_get_constraintdef(oid)
                       FROM pg_constraint WHERE connamespace=(SELECT oid FROM pg_namespace
                         WHERE nspname=current_schema())
                       AND conrelid::regclass::text IN
                         ('ingestion_run','source_response','event_version','event_current',
                          'quarantine_record','historical_interval_checkpoint',
                          'replay_event_version','replay_event_current')
                       ORDER BY conrelid::regclass::text,conname""")
        constraints = cur.fetchall()
    print(json.dumps({'source_run':source_run,'run_versions':run_versions,'versions':versions,'current':current,
                      'asof':asof,'indexes':indexes,'constraints':constraints}, default=str))
finally:
    conn.rollback()
    conn.close()
'''


def milliseconds(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def read_original(run_id: str) -> tuple[dict, str, Path]:
    path = EVIDENCE / "originals" / run_id / "response.json"
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest(), path


def api(path: str, query: dict) -> dict:
    url = f"http://127.0.0.1:8000{path}?{urlencode(query)}"
    with urlopen(url, timeout=8) as response:
        return json.load(response)


def main() -> None:
    monitor_path = EVIDENCE / "monitor-entrega-20261118.jsonl"
    monitor = next(json.loads(line) for line in monitor_path.read_text(encoding="utf-8").splitlines()
                   if json.loads(line)["sampled_at"] == SAMPLE)
    if monitor["source_last_fetch"]["run_id"] != RUN:
        raise RuntimeError("La muestra no corresponde al run solicitado")
    document, sha, source_path = read_original(RUN)
    start_ms, end_ms = milliseconds(START), milliseconds(END)
    raw_features = document["payload"]["features"]
    earthquakes = [f for f in raw_features if f.get("properties", {}).get("type") == "earthquake"]
    non_earthquakes = [{"event_id": f.get("id"), "type": f.get("properties", {}).get("type")}
                       for f in raw_features if f.get("properties", {}).get("type") != "earthquake"]
    in_window = [f for f in earthquakes if isinstance(f.get("properties", {}).get("time"), int)
                 and start_ms <= f["properties"]["time"] < end_ms]
    source = {f["id"]: f["properties"]["updated"] for f in in_window}
    db_process = subprocess.run(
        ["docker", "compose", "exec", "-T", "consumer", "python", "-c", DB_CODE,
         str(start_ms), str(end_ms), SAMPLE, RUN], cwd=ROOT, text=True,
        capture_output=True, timeout=25, check=True,
    )
    db = json.loads(db_process.stdout.strip().splitlines()[-1])
    query = {"mode": "live", "start": START, "end": END}
    api_started = datetime.now(timezone.utc).isoformat()
    pages = []
    api_features = []
    for page in range(1, 11):
        result = api("/api/eventos", {**query, "page": page, "page_size": 100})
        pages.append({"page": page, "count": result["metadata"]["count"],
                      "total": result["metadata"]["total"],
                      "generated": result["metadata"]["generated"]})
        api_features.extend(result["features"])
        if not result["metadata"]["truncated"]:
            break
    else:
        raise RuntimeError("La paginación superó diez páginas")
    stats = api("/api/estadisticas", query)
    api_finished = datetime.now(timezone.utc).isoformat()
    api_ids = {f["id"]: f["properties"]["updated"] for f in api_features}
    current = {row[0]: row for row in db["current"]}
    asof = {row[0]: row for row in db["asof"]}
    versions = db["versions"]
    version_asof = [row for row in versions if datetime.fromisoformat(row[3]) <= datetime.fromisoformat(SAMPLE)]
    version_pairs_asof = {(row[0], row[1]) for row in version_asof}
    extra_ids = sorted((set(current) | set(asof) | set(api_ids)) - set(source))
    prior = []
    for event_id in extra_ids:
        matches = [row for row in versions if row[0] == event_id]
        if not matches:
            continue
        first = min(matches, key=lambda row: row[3])
        prior_document, prior_sha, prior_path = read_original(first[4])
        verified = any(f.get("id") == event_id and f.get("properties", {}).get("updated") == first[1]
                       for f in prior_document["payload"].get("features", []))
        prior.append({"event_id": event_id, "version_updated": first[1],
                      "first_version_run": first[4], "response_id": first[5],
                      "response_received_at": first[6],
                      "original_path": str(prior_path.relative_to(ROOT)).replace("\\", "/"),
                      "original_sha256": prior_sha, "id_updated_verified_in_original": verified})
    report = {
        "audited_at_utc": api_finished, "monitor_sample_utc": SAMPLE,
        "monitor_observation": {"source_last_fetch": monitor["source_last_fetch"],
                                "live_24h": monitor["counts"]["live_24h"],
                                "errors": monitor["errors"]},
        "source_run": RUN, "source_path": str(source_path.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha, "source_metadata": document["metadata"],
        "source_run_db": db["source_run"],
        "source_run_versions": db["run_versions"],
        "window_utc": {"start_inclusive": START, "end_exclusive": END},
        "filters": {"mode": "live", "type": "earthquake", "min_mag": None,
                    "country_id": None, "min_depth_km": None, "max_depth_km": None,
                    "synthetic": False},
        "source_counts": {"features": len(raw_features), "unique_ids": len({f.get('id') for f in raw_features}),
                          "earthquakes": len(earthquakes),
                          "earthquakes_in_window": len(in_window), "unique_ids_in_window": len(source),
                          "non_earthquakes": non_earthquakes,
                          "earthquakes_outside_window": sorted({f["id"] for f in earthquakes} - set(source))},
        "db_counts": {"version_rows_in_window": len(versions),
                      "version_ids_in_window": len({r[0] for r in versions}),
                      "version_rows_at_sample": len(version_asof),
                      "version_ids_at_sample": len({r[0] for r in version_asof}),
                      "current_ids_in_window_at_audit": len(current),
                      "reconstructed_ids_at_sample": len(asof)},
        "api_counts": {"query_started_at_utc": api_started, "query_finished_at_utc": api_finished,
                       "pages": pages, "unique_ids": len(api_ids), "statistics_count": stats["count"],
                       "statistics_country_sum": sum(c["count"] for c in stats["countries"])},
        "differences": {
            "source_only_vs_current": sorted(set(source) - set(current)),
            "current_only_vs_source": sorted(set(current) - set(source)),
            "source_only_vs_asof": sorted(set(source) - set(asof)),
            "asof_only_vs_source": sorted(set(asof) - set(source)),
            "source_id_updated_missing_in_versions_at_sample": [
                {"event_id": event_id, "updated": updated}
                for event_id, updated in sorted(source.items())
                if (event_id, updated) not in version_pairs_asof
            ],
            "source_only_vs_api": sorted(set(source) - set(api_ids)),
            "api_only_vs_source": sorted(set(api_ids) - set(source)),
            "current_only_vs_api": sorted(set(current) - set(api_ids)),
            "api_only_vs_current": sorted(set(api_ids) - set(current)),
            "updated_mismatch_current_api": [
                {"event_id": k, "current": current[k][1], "api": api_ids[k]}
                for k in sorted(set(current) & set(api_ids)) if current[k][1] != api_ids[k]
            ],
            "updated_mismatch_source_current": [
                {"event_id": k, "source": source[k], "current": current[k][1]}
                for k in sorted(set(source) & set(current)) if source[k] != current[k][1]
            ],
            "updated_mismatch_source_asof": [
                {"event_id": k, "source": source[k], "asof": asof[k][1]}
                for k in sorted(set(source) & set(asof)) if source[k] != asof[k][1]
            ],
        },
        "additional_id_provenance": prior,
        "indexes": [{"name": r[0], "bytes": r[1], "definition": r[2],
                     "unique": r[3], "idx_scan_since_stats_reset": r[4]} for r in db["indexes"]],
        "constraints": db["constraints"],
        "limit": "El monitor guardó recuentos, no IDs de la respuesta API. La reconstrucción SQL usa ingested_at <= sampled_at y no demuestra el conjunto exacto que respondió la API unos instantes después.",
    }
    output = ROOT / "evidence/002-ingesta-usgs-persistencia/audit-monitor-1723-20261118.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("source_sha256", "source_counts", "db_counts", "api_counts", "differences", "additional_id_provenance")}, ensure_ascii=False, indent=2))
    print(f"Informe: {output}")


if __name__ == "__main__":
    main()
