"""Tests use fabricated records; no fake data are claimed to be Azure measurements."""
from __future__ import annotations
import sqlite3
import zipfile
from pathlib import Path
import pytest
from capacity_intelligence.ingest import (
    adapt_options, adapt_requests, discover_tables, iterate_rows, sqlite_members
)


def create_fixture(db_path: Path) -> None:
    with sqlite3.connect(db_path) as db:
        db.execute('''CREATE TABLE arbitrary_request_name (
          vmId INTEGER, tenantId INTEGER, vmTypeId INTEGER,
          priority INTEGER, starttime REAL, endtime REAL)''')
        db.executemany('''INSERT INTO arbitrary_request_name VALUES (?,?,?,?,?,?)''', [
            (101, 20, 1, 0, -1.0, 3.25),
            (102, 21, 1, 1, 0.2, None),
            (103, 21, 2, 0, 2.0, 8.0),
        ])
        db.execute('''CREATE TABLE arbitrary_type_name (
            id INTEGER, vmTypeId INTEGER, machineId INTEGER, core REAL,
            memory REAL, hdd REAL, ssd REAL, nic REAL)''')
        db.executemany('''INSERT INTO arbitrary_type_name VALUES (?,?,?,?,?,?,?,?)''', [
            (1, 1, 9, .25, .5, .1, .1, .05), (2, 2, 9, .50, .7, .2, .2, .1)
        ])


def test_discovers_upstream_tables_by_columns(tmp_path):
    path = tmp_path / "fixture.sqlite"
    create_fixture(path)
    with sqlite3.connect(path) as con:
        assert discover_tables(con) == ("arbitrary_request_name", "arbitrary_type_name")
        rows = list(iterate_rows(con, "arbitrary_request_name",
            ("vmid", "tenantid", "vmtypeid", "priority", "starttime", "endtime"),
            batch_size=2, max_rows=2))
    assert len(rows) == 1 and len(rows[0]) == 2
    assert adapt_requests("part-1.sqlite", rows[0])[0] == (
        "part-1.sqlite", "101", "20", "1", 0, -1.0, 3.25)


def test_censored_end_and_scoped_ids():
    values = adapt_requests("different.sqlite", [(102, 21, 1, 1, .2, None)])
    assert values[0][0] == "different.sqlite" and values[0][-1] is None
    assert adapt_options("source.db", [(1, 2, 3, .25, .5, 0, 0, .1)])[0][:4] == (
        "source.db", "1", "2", "3")


def test_missing_fields_fails(tmp_path):
    path = tmp_path / "bad.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE unhelpful (id INT)")
        with pytest.raises(ValueError, match="lacks documented"):
            discover_tables(db)


def test_zip_member_discovery(tmp_path):
    zpath = tmp_path / "fixture.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("trace/sub/file.sqlite", b"SQLite format 3\\0")
        zf.writestr("trace/README.txt", "readme")
    with zipfile.ZipFile(zpath) as zf:
        assert [x.filename for x in sqlite_members(zf)] == ["trace/sub/file.sqlite"]
