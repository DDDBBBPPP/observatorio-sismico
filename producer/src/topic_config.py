import os


EXPECTED_PARTITIONS = 1
EXPECTED_REPLICATION_FACTOR = 1


def validated_topic_shape() -> tuple[int, int]:
    raw_partitions = os.environ.get("KAFKA_TEST_PARTITIONS", "1")
    raw_replication = os.environ.get("KAFKA_TEST_REPLICATION_FACTOR", "1")
    try:
        partitions = int(raw_partitions)
    except ValueError as exc:
        raise RuntimeError(
            f"KAFKA_TEST_PARTITIONS debe ser {EXPECTED_PARTITIONS}; recibido {raw_partitions!r}"
        ) from exc
    try:
        replication_factor = int(raw_replication)
    except ValueError as exc:
        raise RuntimeError(
            "KAFKA_TEST_REPLICATION_FACTOR debe ser "
            f"{EXPECTED_REPLICATION_FACTOR}; recibido {raw_replication!r}"
        ) from exc
    if partitions != EXPECTED_PARTITIONS:
        raise RuntimeError(
            f"KAFKA_TEST_PARTITIONS debe ser {EXPECTED_PARTITIONS}; recibido {partitions}"
        )
    if replication_factor != EXPECTED_REPLICATION_FACTOR:
        raise RuntimeError(
            "KAFKA_TEST_REPLICATION_FACTOR debe ser "
            f"{EXPECTED_REPLICATION_FACTOR}; recibido {replication_factor}"
        )
    return EXPECTED_PARTITIONS, EXPECTED_REPLICATION_FACTOR
