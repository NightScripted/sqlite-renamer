# Planning benchmark

`benchmark_planning.py` creates an invented, disposable SQLite database with one file, performer, and studio per scene. It measures the current query shape used by `$performer - $studio - $title`; it does not read a Stash database or media files.

Run it from the repository root:

```bash
python benchmarks/benchmark_planning.py --sizes 100,1000
```

The macOS baseline recorded on 2026-08-24 with Python 3.14.7 was:

| Scenes | Operations | SQL statements | Elapsed | Peak Python allocation |
|---:|---:|---:|---:|---:|
| 100 | 100 | 301 | 0.015448 s | 74,859 bytes |
| 1,000 | 1,000 | 3,001 | 0.189614 s | 710,996 bytes |

The result confirms the known `3N + 1` query shape for this metadata-rich template. It is a baseline, not a reason to optimize yet: compare the same command on a representative size before changing the planner, and agree a latency or memory threshold first.
