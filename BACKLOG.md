# Backlog

Issues and improvements to address in future sessions. Ordered by priority within each section.

---

## P0 — Critical

<!--
- [ ] **Short title** — `File.py:line`
  Description of the problem and its impact. Fix: what to change.
-->

## P1 — Important

- [ ] **Multiple configured tags are not first-match-only** — `run_renamer.py:27-42`
  A scene carrying more than one configured tag is submitted to every matching pass. In a live run, the first pass renames the file but the database remains read-only with its original basename, so a later matching pass looks for the old path and reports it missing. Keep tag rules mutually exclusive until the runner excludes scenes already handled by an earlier pass.

## P2 — Code quality / gaps

## P3 — Polish
