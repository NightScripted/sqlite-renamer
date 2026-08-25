# Planning benchmark

`benchmark_planning.py` creates an invented, disposable SQLite database with one file, performer, and studio per scene. It measures the current query shape used by `$performer - $studio - $title`; it does not read a Stash database or media files.

Run it from the repository root:

```bash
python benchmarks/benchmark_planning.py --sizes 100,1000
```

The macOS baseline revalidated on 2026-08-25 with Python 3.14.7 was:

| Scenes | Operations | SQL statements | Elapsed | Peak Python allocation |
|---:|---:|---:|---:|---:|
| 100 | 100 | 301 | 0.016232 s | 75,299 bytes |
| 1,000 | 1,000 | 3,001 | 0.197082 s | 711,044 bytes |

The result confirms the known `3N + 1` query shape for this metadata-rich template. Elapsed time and peak allocation naturally vary by host and runtime, so compare the same command on a representative size before changing the planner. This is a baseline, not a reason to optimize yet; agree a latency or memory threshold first.
