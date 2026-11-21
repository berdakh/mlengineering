"""Challenge: right result on both databases, plus a declared grain whose key really is a key."""
from __future__ import annotations

import pytest

import w2d1_harness as H
import w2d1_oracle as O


@pytest.mark.parametrize("db_name", ["committed", "reseeded"])
@pytest.mark.parametrize("query", sorted(O.CHALLENGE))
def test_query_result(query, db_name, target, databases, tables):
    oracle, _ = O.CHALLENGE[query]
    columns, rows = oracle(tables[db_name])
    got = H.run_query(databases[db_name], target / "queries" / f"{query}.sql")
    H.assert_same_result(got, columns, rows, label=f"{query} on the {db_name} database")


@pytest.mark.parametrize("db_name", ["committed", "reseeded"])
@pytest.mark.parametrize("query", sorted(O.CHALLENGE))
def test_declared_key_is_unique_and_minimal(query, db_name, target, databases):
    path = target / "queries" / f"{query}.sql"
    grain = H.declared_header(path, "grain")
    key = H.declared_header(path, "key")
    assert grain and "todo" not in grain.lower(), f"{query}.sql: write the '-- grain: ...' line"
    assert key and "todo" not in key.lower(), f"{query}.sql: write the '-- key: col[, col]' line"
    key_cols = [c.strip().lower() for c in key.split(",") if c.strip()]
    columns, rows = H.run_query(databases[db_name], path)
    for c in key_cols:
        assert c in columns, f"{query}.sql: declared key column '{c}' is not in the result"
    values = [tuple(r[columns.index(c)] for c in key_cols) for r in rows]
    assert len(values) == len(set(values)), (
        f"{query}.sql: declared key {key_cols} is not unique in the result on the {db_name} database")
    expected_key = O.CHALLENGE[query][1]
    assert sorted(key_cols) == sorted(expected_key), (
        f"{query}.sql: the declared key {key_cols} is unique but not the minimal key of the requested grain")
