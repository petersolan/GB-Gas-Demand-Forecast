# Live track record

Day-ahead forecasts issued daily by the champion model (`.github/workflows/daily-forecast.yml`), scored against quality-checked actuals. Last 28 days with actuals: 16 Oct to 21 Oct 2026 (6 gas days, 75 LDZ-days scored).

| | MAPE |
| --- | --- |
| Model | 4.24% |
| National Gas day-ahead | 4.29% |

P10-P90 range coverage: 91% (target 80%).

No drift: the model is level with or ahead of the benchmark.

## By gas day

| Gas day | Model MAPE | National Gas MAPE |
| --- | --- | --- |
| Wed 21 Oct | 5.49% | 5.99% |
| Tue 20 Oct | 4.35% | 4.72% |
| Mon 19 Oct | 3.89% | 3.54% |
| Sun 18 Oct | 5.16% | 3.33% |
| Sat 17 Oct | 3.43% | 5.05% |
| Fri 16 Oct | 3.04% | 3.01% |

Full detail per LDZ in [scores.csv](scores.csv).
