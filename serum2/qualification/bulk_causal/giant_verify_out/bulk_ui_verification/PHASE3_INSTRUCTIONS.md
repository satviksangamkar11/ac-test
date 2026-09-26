# Phase 3B/3C — live MCP execution run (no GUI, no clicking)

This runs every MCP control edit against a real headless Serum through DawDreamer, the same way the campaign and
`dump_reference_parameter_text.py` already ran on this machine. Ableton and the Serum window are NOT used: do not
open, click or change anything in them.

## Step 0 — update and recheck the 3 rows that stopped the first smoke run

The first smoke run stopped on `oscA.warp_mode2`, `arp.playback.offset` and `global.voice_priority`. All three
were fixed on the cloud side (a side-leaf judging bug, a 0.0 default test value, and a sentinel string Serum
drops). From the repo root:

```
git pull origin claude/quirky-franklin-a9x2d3
python serum2/qualification/bulk_causal/run_mcp_execution_harness.py --ids oscA.warp_mode2,arp.playback.offset,global.voice_priority --out serum2/qualification/bulk_causal/giant_verify_out/bulk_ui_verification/mcp_exec_recheck_results.jsonl
```

Keep that file; it is pushed in Step 4. Then continue with Step 1 regardless of what it printed.

## Step 1 — smoke run (~43 rows, a few minutes)

```
python serum2/qualification/bulk_causal/run_mcp_execution_harness.py --sample
```

This overwrites the earlier sample results file; that is intended.

It prints progress and a final line like `done: {"MCP_EXEC_HOST_CONFIRMED": ..., ...}`.
Output file: `serum2/qualification/bulk_causal/giant_verify_out/bulk_ui_verification/mcp_exec_sample_results.jsonl`

If it stops with `SamplesFolderNotFoundError`, set the samples folder once and re-run the same command:

```
set SERUM_SAMPLES_PATH=<your Serum "Samples" folder, the sibling of its "Presets" folder>
```

If it stops with any other error, do not try to fix it: commit and push whatever results file exists plus the
full error text in a file named `phase3_error.txt`, and stop.

## Step 2 — decide whether to continue (mechanical rule, no judgement)

Look only at the final `done:` line of Step 1.

- If `MCP_EXEC_FAILED` and `MCP_EXEC_NOOP_SUSPECT` are both absent or 0: go to Step 3.
- Otherwise: skip Step 3. Commit and push the sample results file and stop.

## Step 3 — full run (330 rows, resumable)

```
python serum2/qualification/bulk_causal/run_mcp_execution_harness.py --all --resume
```

If it is interrupted for any reason, run the exact same command again: `--resume` skips rows already done.
Output file: `.../bulk_ui_verification/mcp_exec_all_results.jsonl`

## Step 4 — push

```
git add -f serum2/qualification/bulk_causal/giant_verify_out/bulk_ui_verification/mcp_exec_*_results.jsonl
git commit -m "Phase 3 live MCP execution results"
git push origin HEAD:claude/direct-ui-rescan-2026-09-26
```

If that push is refused, push to a new branch instead and say which one:
`git push origin HEAD:refs/heads/claude/phase3-results-2026-09-27`. The first smoke-run push never reached the
remote, so check `git log origin/<branch> -1` after pushing.

Do not interpret, summarise or edit the results. The report is built from the files on the cloud side.
