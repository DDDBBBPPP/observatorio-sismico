"""Run depth predicates against a temporary PostgreSQL table in the API container."""
from src.db import connection
from src.main import filters, parse_depth_range


with connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("CREATE TEMP TABLE depth_fixture (event_time BIGINT, mag DOUBLE PRECISION, depth_km DOUBLE PRECISION, country_id TEXT)")
        cursor.executemany("INSERT INTO depth_fixture VALUES (50, 4, %s, NULL)",
                           [(None,), (-2,), (0,), (70,), (300,)])
        for lower, upper, expected in ((None, None, 5), (0, 70, 2),
                                       (70, 300, 2), (-2, 0, 2),
                                       (None, -2, 1), (300, None, 1)):
            where, params = filters(0, 100, None, None, lower, upper,
                                    alias="c", real_only=False)
            cursor.execute(f"SELECT COUNT(*) FROM depth_fixture c WHERE {where}", params)
            assert cursor.fetchone()[0] == expected, (lower, upper)

assert parse_depth_range("-2", "0") == (-2, 0)
print("depth SQL rules: passed (nulls, inclusive bounds, negatives)")
