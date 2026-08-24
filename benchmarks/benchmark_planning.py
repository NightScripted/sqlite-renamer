"""Measure privacy-safe query, memory, and elapsed-time planning baselines."""

from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db import Database  # noqa: E402
from planning import discover_operations  # noqa: E402


def _create_fixture(database_path: Path, scene_count: int) -> None:
    """Create an invented supported-schema fixture with one file per scene."""
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE scenes (id INTEGER PRIMARY KEY, title TEXT, date TEXT, studio_id INTEGER);
        CREATE TABLE scenes_files (scene_id INTEGER, file_id INTEGER);
        CREATE TABLE files (id INTEGER PRIMARY KEY, basename TEXT, parent_folder_id INTEGER);
        CREATE TABLE folders (id INTEGER PRIMARY KEY, path TEXT);
        CREATE TABLE video_files (file_id INTEGER, height INTEGER);
        CREATE TABLE performers_scenes (scene_id INTEGER, performer_id INTEGER);
        CREATE TABLE performers (id INTEGER PRIMARY KEY, name TEXT, gender TEXT);
        CREATE TABLE studios (id INTEGER PRIMARY KEY, name TEXT);
        """
    )
    connection.execute("INSERT INTO folders VALUES (1, '/fixture')")
    connection.execute("INSERT INTO studios VALUES (1, 'Fixture Studio')")
    connection.execute("INSERT INTO performers VALUES (1, 'Fixture Performer', 'FEMALE')")
    connection.executemany(
        "INSERT INTO scenes VALUES (?, ?, '2026-01-01', 1)",
        ((number, "Fixture Title {:06d}".format(number)) for number in range(1, scene_count + 1)),
    )
    connection.executemany(
        "INSERT INTO files VALUES (?, ?, 1)",
        ((number, "source-{:06d}.mp4".format(number)) for number in range(1, scene_count + 1)),
    )
    connection.executemany(
        "INSERT INTO scenes_files VALUES (?, ?)",
        ((number, number) for number in range(1, scene_count + 1)),
    )
    connection.executemany(
        "INSERT INTO video_files VALUES (?, 1080)",
        ((number,) for number in range(1, scene_count + 1)),
    )
    connection.executemany(
        "INSERT INTO performers_scenes VALUES (?, 1)",
        ((number,) for number in range(1, scene_count + 1)),
    )
    connection.commit()
    connection.close()


def benchmark(scene_count: int) -> dict[str, int | float]:
    """Measure one fully populated synthetic fixture size."""
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "fixture.sqlite"
        _create_fixture(database_path, scene_count)
        connection = sqlite3.connect(database_path.as_uri() + "?mode=ro", uri=True)
        query_count = 0

        def count_query(_: str) -> None:
            nonlocal query_count
            query_count += 1

        connection.set_trace_callback(count_query)
        database = Database(connection, connection.cursor())
        tracemalloc.start()
        started = time.perf_counter()
        operations = discover_operations(database, "$performer - $studio - $title")
        elapsed_seconds = time.perf_counter() - started
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        database.close()
    return {
        "scene_count": scene_count,
        "operation_count": len(operations),
        "query_count": query_count,
        "elapsed_seconds": round(elapsed_seconds, 6),
        "peak_bytes": peak_bytes,
    }


def main(argv: list[str] | None = None) -> None:
    """Run one or more fixture sizes and emit machine-readable results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="100,1000", help="comma-separated scene counts")
    args = parser.parse_args(argv)
    sizes = [int(value) for value in args.sizes.split(",")]
    if not sizes or any(size < 1 for size in sizes):
        parser.error("--sizes must contain positive integers")
    print(
        json.dumps(
            {
                "environment": {
                    "python": platform.python_version(),
                    "platform": platform.platform(),
                },
                "results": [benchmark(size) for size in sizes],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
