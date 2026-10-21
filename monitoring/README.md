# Live track record

Day-ahead forecasts issued daily by the champion model (`.github/workflows/daily-forecast.yml`), scored against quality-checked actuals. Last 28 days with actuals: 16 Oct to 20 Oct 2026 (5 gas days, 61 LDZ-days scored).

| | MAPE |
| --- | --- |
| Model | 3.81% |
| National Gas day-ahead | 3.78% |

P10-P90 range coverage: 93% (target 80%).

No drift: the model is level with or ahead of the benchmark.

## By gas day

| Gas day | Model MAPE | National Gas MAPE |
| --- | --- | --- |
| Tue 20 Oct | 4.35% | 4.72% |
| Mon 19 Oct | 3.03% | 2.73% |
| Sun 18 Oct | 5.16% | 3.33% |
| Sat 17 Oct | 3.43% | 5.05% |
| Fri 16 Oct | 3.04% | 3.01% |

Full detail per LDZ in [scores.csv](scores.csv).
