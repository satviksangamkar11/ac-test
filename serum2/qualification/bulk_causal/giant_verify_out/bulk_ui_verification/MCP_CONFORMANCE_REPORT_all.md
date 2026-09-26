# MCP conformance report (all)

Source: `mcp_exec_all_results.jsonl`. Rows: 330.

| outcome | rows |
|---|---|
| MCP_EXEC_HOST_CONFIRMED | 183 |
| MCP_EXEC_CONFIRMED | 0 |
| MCP_EXEC_RAW_ONLY | 127 |
| MCP_EXEC_CONFORMANCE_EXCEPTION | 20 |
| MCP_EXEC_NOOP_SUSPECT | 0 |
| MCP_EXEC_FAILED | 0 |

## Bucket D -- observed vs oracle (20)

- `arp.transpose.range`: plainParams/kParamTransposeRange: wrote 16.0, Serum before None, after 8.0 | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: written 16 displayed as 8; Serum's usable range is narrower than declared
- `fx.compressor.attack`: plainParams/kParamAttack: wrote 100.00000000000001, Serum before None, after 100.00000000000001 | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: displays raw ms with a numeric ratio, raw/100 ms only when ratio shows 'Limit' (control-map v8)
- `fx.compressor.ratio`: plainParams/kParamRatio: wrote 100.0, Serum before None, after 100.0 | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: raw==display for 1-8; 20 shows '32:1'; >=100 (and every value the campaign used, 210/430/31622) shows 'Limit'
- `fx.compressor.release`: plainParams/kParamRelease: wrote 0.1, Serum before None, after 0.10000000149011612 | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: displays raw ms directly; the declared minimum 0.1 shows 1000 (schema minimum invalid)
- `global.fx_bus1_destination`: plainParams/kParamFXBus1Dest: wrote 1.0, Serum before None, after 1.0 | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: schema word 'master' (raw 1.0) displays DIRECT
- `global.fx_bus2_destination`: plainParams/kParamFXBus2Dest: wrote 2.0, Serum before None, after 2.0 | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: schema word 'direct' (raw 2.0) displays BUS 1
- `global.use_ultra_on_render`: plainParams/kParamUseUltraOnRender: wrote 1.0, Serum before None, after None | named None: None -> None | hosts changed: [] | oracle: EXPECT NO DIFF: confirmed by direct toggle+save+diff test not persisted into any preset
- `global.voice_priority`: plainParams/kParamVoicePriority: wrote 'Low', Serum before None, after 'Low' | named None: None -> None | hosts changed: [] | oracle: EXCEPTION: serum-mcp accepts any string for voice_priority, Serum silently drops unknown words (smoke run: 'MCP_TEST' not persisted); re-tested with 'Low'
- `macro1.name`: Macro0/name: wrote 'MCP_TEST', Serum before None, after None | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: Serum shows 'Macro 1', never the written name
- `macro2.name`: Macro1/name: wrote 'MCP_TEST', Serum before None, after None | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: Serum shows 'Macro 2', never the written name
- `macro3.name`: Macro2/name: wrote 'MCP_TEST', Serum before None, after None | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: Serum shows 'Macro 3', never the written name
- `macro4.name`: Macro3/name: wrote 'MCP_TEST', Serum before None, after None | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: Serum shows 'Macro 4', never the written name
- `macro5.name`: Macro4/name: wrote 'MCP_TEST', Serum before None, after None | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: Serum shows 'Macro 5', never the written name
- `macro6.name`: Macro5/name: wrote 'MCP_TEST', Serum before None, after None | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: Serum shows 'Macro 6', never the written name
- `macro7.name`: Macro6/name: wrote 'MCP_TEST', Serum before None, after None | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: Serum shows 'Macro 7', never the written name
- `macro8.name`: Macro7/name: wrote 'MCP_TEST', Serum before None, after None | named None: None -> None | hosts changed: [] | oracle: DIVERGENT: Serum shows 'Macro 8', never the written name
- `mixer.noise.pan`: plainParams/kParamPan: wrote -20.0, Serum before None, after -20.0 | named None: None -> None | hosts changed: ['Noise Pan'] | oracle: DIVERGENT: display is written+1 toward zero (e.g. -20 -> '-19 L')
- `mixer.sub.pan`: plainParams/kParamPan: wrote -4.0, Serum before None, after -4.0 | named None: None -> None | hosts changed: ['Sub Pan'] | oracle: DIVERGENT: display is written+1 toward zero (e.g. -4 -> '-3 L')
- `oscA.warp_amount`: plainParams/kParamWarp: wrote 0.5, Serum before None, after 0.5 | named None: None -> None | hosts changed: ['A Warp'] | oracle: EXPECT MONOTONIC, NO EXACT VALUE: Sync-mode display likely quantized, no smooth curve fits 8 points
- `oscNoise.pan`: plainParams/kParamPan: wrote -20.0, Serum before None, after -20.0 | named None: None -> None | hosts changed: ['Noise Pan'] | oracle: DIVERGENT: alias of mixer.noise.pan, same off-by-one

## New host identities found by scan -- feed back into the crosswalk (9)

- `global.direct_volume`: ['Direct Vol']
- `global.fx_bus1_volume`: ['Bus 1 Vol']
- `global.fx_bus2_volume`: ['Bus 2 Vol']
- `global.global_tuning`: ['Filter 1 Freq', 'Filter 2 Freq']
- `global.swing_div`: ['Swing Div']
- `global.voice_amp`: ['Amp']
- `global.voice_control.random.cutoff`: ['Cutoff Rand']
- `global.voice_control.random.detune`: ['Osc Detune Rnd']
- `global.voice_control.random.envs`: ['Env Rand']
