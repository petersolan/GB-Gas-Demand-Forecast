# Live track record

Day-ahead forecasts issued daily by the champion model (`.github/workflows/daily-forecast.yml`), scored against quality-checked actuals. Last 28 days with actuals: 16 Oct to 23 Oct 2026 (8 gas days, 103 LDZ-days scored).

| | MAPE |
| --- | --- |
| Model | 4.25% |
| National Gas day-ahead | 4.26% |

P10-P90 range coverage: 91% (target 80%).

No drift: the model is level with or ahead of the benchmark.

## By gas day

| Gas day | Model MAPE | National Gas MAPE |
| --- | --- | --- |
| Fri 23 Oct | 4.42% | 3.24% |
| Thu 22 Oct | 3.81% | 5.13% |
| Wed 21 Oct | 5.49% | 5.99% |
| Tue 20 Oct | 4.35% | 4.72% |
| Mon 19 Oct | 3.89% | 3.54% |
| Sun 18 Oct | 5.05% | 3.61% |
| Sat 17 Oct | 3.90% | 4.74% |
| Fri 16 Oct | 3.04% | 3.01% |

Full detail per LDZ in [scores.csv](scores.csv).
