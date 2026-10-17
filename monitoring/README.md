# Live track record

Day-ahead forecasts issued daily by the champion model (`.github/workflows/daily-forecast.yml`), scored against quality-checked actuals. Last 28 days with actuals: 16 Oct to 16 Oct 2026 (1 gas days, 13 LDZs).

| | MAPE |
| --- | --- |
| Model | 3.04% |
| National Gas day-ahead | 3.01% |

P10-P90 range coverage: 100% (target 80%).

No drift: the model is level with or ahead of the benchmark.

## By gas day

| Gas day | Model MAPE | National Gas MAPE |
| --- | --- | --- |
| Fri 16 Oct | 3.04% | 3.01% |

Full detail per LDZ in [scores.csv](scores.csv).
