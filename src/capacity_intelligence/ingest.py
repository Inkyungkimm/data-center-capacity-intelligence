"""Stream Microsoft's public Azure Trace for Packing from SQLite files into Postgres.

Upstream docs: https://github.com/Azure/AzurePublicDataset/blob/master/AzureTracesForPacking2020.md

Raw identifiers are unique only within *one* source SQLite file. The pipeline
preserves file provenance and uses composite keys for safe reruns.
"""
from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import tempfile
import urllib.request
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

LOG = logging.getLogger(__name__)
SOURCE_URL = (
    "https://github.com/Azure/AzurePublicDataset/releases/download/"
    "dataset-packing-2020/azurevmallocation_dataset2020_AzurePackingTraceV1.zip"
)
REQUEST_COLUMNS = ("vmid", "tenantid", "vmtypeid", "priority", "starttime", "endtime")
TYPE_COLUMNS = ("id", "vmtypeid", "machineid", "core", "memory", "hdd", "ssd", "nic")


def discover_tables(connection: sqlite3.Connection) -> tuple[str, str]:
    """Locate upstream tables by column signatures, not guessed table names."""
    found: dict[str, str] = {}
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    for (name,) in tables:
        # quote identifiers properly even when source name includes a quote
        quoted = '"' + name.replace('"', '""') + '"'
        columns = {row[1].lower() for row in connection.execute(f"PRAGMA table_info({quoted})")}
        if set(REQUEST_COLUMNS).issubset(columns):
            if "requests" in found:
                raise ValueError("Multiple matching VM request tables; specify an unambiguous source")
            found["requests"] = name
        if set(TYPE_COLUMNS).issubset(columns):
            if "types" in found:
                raise ValueError("Multiple matching VM type tables; specify an unambiguous source")
            found["types"] = name
    if "requests" not in found or "types" not in found:
        raise ValueError(
            "SQLite file lacks documented VM request or VM type fields. "
            f"Found tables: {[x[0] for x in tables]}"
        )
    return found["requests"], found["types"]


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def iterate_rows(db: sqlite3.Connection, table: str, columns: tuple[str, ...],
                 batch_size: int = 5000, max_rows: int = 0) -> Iterator[list[tuple]]:
    names = {row[1].lower(): row[1] for row in db.execute(f"PRAGMA table_info({quote_identifier(table)})")}
    cols = ", ".join(quote_identifier(names[column]) for column in columns)
    cursor = db.execute(f"SELECT {cols} FROM {quote_identifier(table)}")
    read = 0
    while True:
        n = batch_size if max_rows == 0 else min(batch_size, max_rows - read)
        if n <= 0:
            break
        batch = cursor.fetchmany(n)
        if not batch:
            break
        read += len(batch)
        yield batch


def create_raw_schema(pg) -> None:
    with pg.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS raw")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw.vm_requests (
                source_file TEXT NOT NULL,
                vm_id TEXT NOT NULL,
                tenant_id TEXT,
                vm_type_id TEXT,
                priority INTEGER,
                start_day DOUBLE PRECISION,
                end_day DOUBLE PRECISION,
                ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (source_file, vm_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw.vm_type_options (
                source_file TEXT NOT NULL,
                option_id TEXT NOT NULL,
                vm_type_id TEXT,
                machine_id TEXT,
                cpu_fraction DOUBLE PRECISION,
                memory_fraction DOUBLE PRECISION,
                hdd_fraction DOUBLE PRECISION,
                ssd_fraction DOUBLE PRECISION,
                nic_fraction DOUBLE PRECISION,
                ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (source_file, option_id)
            )
        """)
    pg.commit()


def adapt_requests(source_file: str, rows: list[tuple]) -> list[tuple]:
    return [(source_file, str(r[0]), str(r[1]) if r[1] is not None else None,
             str(r[2]) if r[2] is not None else None, r[3], r[4], r[5]) for r in rows]


def adapt_options(source_file: str, rows: list[tuple]) -> list[tuple]:
    return [(source_file, str(r[0]), str(r[1]) if r[1] is not None else None,
             str(r[2]) if r[2] is not None else None, *r[3:]) for r in rows]


def ingest_sqlite_file(sqlite_path: Path, source_key: str, pg, max_requests: int = 0,
                       batch_size: int = 5000) -> dict[str, int]:
    if not sqlite_path.exists():
        raise FileNotFoundError(sqlite_path)
    create_raw_schema(pg)
    totals = {"vm_requests": 0, "vm_type_options": 0}
    with sqlite3.connect(f"file:{sqlite_path.resolve()}?mode=ro", uri=True) as db:
        request_table, type_table = discover_tables(db)
        tasks = [
            ("vm_type_options", type_table, TYPE_COLUMNS, 0,
             """INSERT INTO raw.vm_type_options
             (source_file,option_id,vm_type_id,machine_id,cpu_fraction,memory_fraction,hdd_fraction,ssd_fraction,nic_fraction)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
             ON CONFLICT (source_file,option_id) DO UPDATE SET
               vm_type_id=EXCLUDED.vm_type_id, machine_id=EXCLUDED.machine_id,
               cpu_fraction=EXCLUDED.cpu_fraction, memory_fraction=EXCLUDED.memory_fraction,
               hdd_fraction=EXCLUDED.hdd_fraction, ssd_fraction=EXCLUDED.ssd_fraction,
               nic_fraction=EXCLUDED.nic_fraction, ingested_at=NOW()""", adapt_options),
            ("vm_requests", request_table, REQUEST_COLUMNS, max_requests,
             """INSERT INTO raw.vm_requests
             (source_file,vm_id,tenant_id,vm_type_id,priority,start_day,end_day)
             VALUES (%s,%s,%s,%s,%s,%s,%s)
             ON CONFLICT (source_file,vm_id) DO UPDATE SET
               tenant_id=EXCLUDED.tenant_id, vm_type_id=EXCLUDED.vm_type_id,
               priority=EXCLUDED.priority, start_day=EXCLUDED.start_day,
               end_day=EXCLUDED.end_day, ingested_at=NOW()""", adapt_requests),
        ]
        for logical_table, actual_table, columns, limit, sql, transform in tasks:
            with pg.cursor() as cursor:
                for rows in iterate_rows(db, actual_table, columns, batch_size, limit):
                    cursor.executemany(sql, transform(source_key, rows))
                    totals[logical_table] += len(rows)
                    pg.commit()
    LOG.info("Processed %s: %s", source_key, totals)
    return totals


def download_archive(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        LOG.info("Using existing archive: %s", target)
        return target
    LOG.info("Downloading official Azure trace from %s", SOURCE_URL)
    try:
        urllib.request.urlretrieve(SOURCE_URL, target)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target


def sqlite_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = [info for info in archive.infolist()
               if not info.is_dir() and info.filename.lower().endswith((".sqlite", ".sqlite3", ".db"))]
    if not members:
        raise ValueError("Archive has no SQLite (.sqlite/.sqlite3/.db) files")
    return members


def run(archive_path: Path, max_files: int, max_requests: int, batch_size: int,
        pg) -> dict[str, int]:
    totals = {"vm_requests": 0, "vm_type_options": 0, "files": 0}
    if archive_path.suffix.lower() in (".sqlite", ".sqlite3", ".db"):
        count = ingest_sqlite_file(archive_path, archive_path.name, pg,
                                   max_requests=max_requests, batch_size=batch_size)
        return {**count, "files": 1}
    with zipfile.ZipFile(archive_path) as zf:
        members = sqlite_members(zf)
        if max_files:
            members = members[:max_files]
        for idx, member in enumerate(members):
            # Do not extract the upstream ZIP member path onto the local filesystem.
            # Stream into a known, safely named temporary destination instead.
            with tempfile.TemporaryDirectory(prefix="azure_capacity_") as temp:
                db_path = Path(temp) / f"trace_{idx}.sqlite"
                with zf.open(member) as inp, db_path.open("wb") as out:
                    import shutil
                    shutil.copyfileobj(inp, out)
                counts = ingest_sqlite_file(db_path, member.filename, pg,
                                            max_requests=max_requests, batch_size=batch_size)
                for key in counts:
                    totals[key] += counts[key]
                totals["files"] += 1
    return totals


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--download", action="store_true", help="Download original Microsoft public ZIP")
    group.add_argument("--archive", type=Path, help="Path to official ZIP or extracted SQLite file")
    parser.add_argument("--max-files", type=int, default=1,
                        help="Number of source SQLite files; 0 for all (default: 1)")
    parser.add_argument("--max-requests", type=int, default=20000,
                        help="VM request rows per SQLite source; 0 for all (default: 20000)")
    parser.add_argument("--batch-size", type=int, default=5000)
    args = parser.parse_args()
    for name in ("max_files", "max_requests", "batch_size"):
        if getattr(args, name) < (1 if name == "batch_size" else 0):
            parser.error(f"--{name.replace('_','-')} must be nonnegative (batch-size >= 1)")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("Install package dependencies: pip install -r requirements.txt") from exc
    path = download_archive(Path("raw_data/azure_packing_2020.zip")) if args.download else args.archive
    conn = psycopg.connect(
        host=os.getenv("PGHOST", "localhost"), port=os.getenv("PGPORT", "5432"),
        user=os.getenv("PGUSER", "analytics"),
        password=os.getenv("PGPASSWORD", "analytics_local_only"),
        dbname=os.getenv("PGDATABASE", "capacity"),
    )
    try:
        result = run(path, args.max_files, args.max_requests, args.batch_size, conn)
    finally:
        conn.close()
    print("Finished ingestion:", result)


if __name__ == "__main__":
    main()
