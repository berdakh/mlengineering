"""Each lab query must return the right result set on the committed database AND on a
re-seeded one (same schema, different rows), so memorised or hard-coded answers fail."""
from __future__ import annotations

import pytest

import w2d1_harness as H
import w2d1_oracle as O


@pytest.mark.parametrize("db_name", ["committed", "reseeded"])
@pytest.mark.parametrize("query", sorted(O.LAB))
def test_query_result(query, db_name, target, databases, tables):
    oracle, ordered = O.LAB[query]
    columns, rows = oracle(tables[db_name])
    got = H.run_query(databases[db_name], target / "queries" / f"{query}.sql")
    H.assert_same_result(got, columns, rows, ordered=ordered, label=f"{query} on the {db_name} database")


@pytest.mark.parametrize("query", sorted(O.LAB))
def test_grain_is_stated(query, target):
    grain = H.declared_header(target / "queries" / f"{query}.sql", "grain")
    assert grain and "todo" not in grain.lower(), (
        f"{query}.sql: state the grain of the result in a '-- grain: ...' comment")
