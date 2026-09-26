# Phase 3E — full re-run with restoration check (no GUI, no clicking)

Phase 3D (the 330/330 run already merged) is being superseded: it never verified that a control returns to its
starting value after the edit. The harness now does a third load -- the same untouched baseline body again -- and
checks every judged leaf lands back where it started (`restoration_verified`). It also stamps the exact Serum
binary's sha256 into every row. Only rows with `restoration_verified: true` and a real `serum_sha256` can become
capability evidence; nothing else changes about how a row runs.

Ableton and the Serum window are NOT used: do not open, click or change anything in them.

## Step 1 — pull

```
git pull origin claude/quirky-franklin-a9x2d3
```

## Step 2 — full run (330 rows, resumable, ~3 loads/row now instead of 2)

```
python serum2/qualification/bulk_causal/run_mcp_execution_harness.py --all --resume --out serum2/qualification/bulk_causal/giant_verify_out/bulk_ui_verification/mcp_exec_all_v2_results.jsonl
```

This is a NEW output file (`_v2_`); it does not touch the Phase 3D file. If it is interrupted, run the exact same
command again -- `--resume` skips rows already done in that file.

If it stops with `SamplesFolderNotFoundError`, set the samples folder once and re-run the same command:

```
set SERUM_SAMPLES_PATH=<your Serum "Samples" folder, the sibling of its "Presets" folder>
```

If it stops with any other error, do not try to fix it: commit and push whatever results file exists plus the
full error text in a file named `phase3e_error.txt`, and stop.

## Step 3 — sanity check before pushing (mechanical, no judgement)

```
python -c "
import json
rows = [json.loads(l) for l in open('serum2/qualification/bulk_causal/giant_verify_out/bulk_ui_verification/mcp_exec_all_v2_results.jsonl')]
print('rows:', len(rows))
print('restoration_verified false:', sum(1 for r in rows if r.get('restoration_verified') is False))
print('failed:', sum(1 for r in rows if r['outcome'] == 'MCP_EXEC_FAILED'))
print('noop_suspect:', sum(1 for r in rows if r['outcome'] == 'MCP_EXEC_NOOP_SUSPECT'))
print('sha values seen:', set(r.get('serum_sha256') for r in rows))
"
```

Expected: 330 rows, 0 restoration failures, 0 FAILED, 0 NOOP_SUSPECT, and exactly one sha value --
`9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3`. If any restoration failures show up, that is
a genuine finding (the edit left Serum in a different state than before it) -- push the file anyway and say so;
do not discard or rerun those rows to make the number look better.

## Step 4 — push

```
git add -f serum2/qualification/bulk_causal/giant_verify_out/bulk_ui_verification/mcp_exec_all_v2_results.jsonl
git commit -m "Phase 3E: full re-run with restoration check + Serum sha stamp"
git push origin HEAD:claude/phase3e-restoration-2026-09-2X
```

Use today's actual date in the branch name. If the push is refused, try a different suffix and say which branch
name you used. Check `git log origin/<branch> -1` after pushing to confirm it landed.

Do not interpret, summarise or edit the results. The report and the binding-evidence conversion are built from
the files on the cloud side.
