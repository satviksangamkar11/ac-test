# FINAL closure report (control map v8) -- 330/330

Every one of the 330 controls now has a terminal conclusion. None remain open.

| conclusion | controls |
|---|---|
| DIRECT_UI_CONFIRMED | 191 |
| UI_OBSERVABLE_BUT_UNREADABLE | 65 |
| HOST_TEXT_VALIDATED | 40 |
| UI_UNOBSERVABLE | 15 |
| UI_MISMATCH | 11 |
| UI_SCHEMA_MISMATCH | 6 |
| RESIDUAL_NOT_STORED | 1 |
| UI_CURVE_UNRESOLVED_FINAL | 1 |

## The last control closed

`oscA.warp_amount` (Sync mode): CLOSED as investigated, not as solved. Full 8-point dataset (Sync mode, A_direct_ui + closure_pass_4/5): 0.05->1.00%, 0.2->1.12%, 0.32->1.49%, 0.46->2.46%, 0.55->3.50%, 0.65->5.12%, 0.9->11.93%, 0.97->14.69%. The write is confirmed correct in every case -- raw changes a distinct, monotonically-increasing percentage on screen every time, never silently dropped or clamped to a repeat value. But no smooth raw->display curve fits: the best 5-point exponential candidate (6.7% max error) got WORSE on the full 8 points (23.9% max error); power-law and a 3-parameter quadratic-in-log-exponent both fit worse still. Adding data made the fit worse, not better -- the likely explanation is that Sync-mode warp snaps to a quantized set of musical ratios (the way filter1.type snaps to named types) rather than following a continuous function, so a smooth-curve model is the wrong shape of answer, not just an imprecise one. Reporting a formula here would be false precision. No further calibration is recommended: this is the map's last item and diminishing returns already showed at 8 points.

