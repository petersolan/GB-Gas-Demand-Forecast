# Live track record

Day-ahead forecasts issued daily by the champion model (`.github/workflows/daily-forecast.yml`), scored against quality-checked actuals. Last 28 days with actuals: 16 Oct to 17 Oct 2026 (2 gas days, 24 LDZ-days scored).

| | MAPE |
| --- | --- |
| Model | 3.24% |
| National Gas day-ahead | 4.03% |

P10-P90 range coverage: 100% (target 80%).

No drift: the model is level with or ahead of the benchmark.

## By gas day

| Gas day | Model MAPE | National Gas MAPE |
| --- | --- | --- |
| Sat 17 Oct | 3.43% | 5.05% |
| Fri 16 Oct | 3.04% | 3.01% |

Full detail per LDZ in [scores.csv](scores.csv).
