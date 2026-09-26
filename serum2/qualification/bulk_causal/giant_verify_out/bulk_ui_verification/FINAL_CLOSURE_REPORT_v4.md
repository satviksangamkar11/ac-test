# FINAL closure report (control map v7)

330 controls. Terminal: 329. Open: 1.

| conclusion | controls |
|---|---|
| DIRECT_UI_CONFIRMED | 191 |
| UI_OBSERVABLE_BUT_UNREADABLE | 65 |
| HOST_TEXT_VALIDATED | 40 |
| UI_UNOBSERVABLE | 15 |
| UI_MISMATCH | 11 |
| UI_SCHEMA_MISMATCH | 6 |
| RESIDUAL_NOT_STORED | 1 |
| UI_LANDED_CURVE_OPEN (open) | 1 |

## Remaining open, exactly

**UI_LANDED_CURVE_OPEN (1)**: `oscA.warp_amount` -- 5-point dataset (0.20->1.12%, 0.32->1.49%, 0.46->2.46%, 0.65->5.12%, 0.90->11.93%, Sync mode): linear is rejected (ratio spans 117%). Best candidate is exponential, display = 0.52*exp(3.47*raw)%, residuals -6.7% to +6.3% -- plausible but not tight enough to call confirmed on 5 points; power-law fits worse (30% max err). Left open as a TENTATIVE exponential fit, not a confirmed curve; more points would settle it.

