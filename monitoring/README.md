# Live track record

Day-ahead forecasts issued daily by the champion model (`.github/workflows/daily-forecast.yml`), scored against quality-checked actuals. Last 28 days with actuals: 16 Oct to 22 Oct 2026 (7 gas days, 89 LDZ-days scored).

| | MAPE |
| --- | --- |
| Model | 4.18% |
| National Gas day-ahead | 4.45% |

P10-P90 range coverage: 91% (target 80%).

No drift: the model is level with or ahead of the benchmark.

## By gas day

| Gas day | Model MAPE | National Gas MAPE |
| --- | --- | --- |
| Thu 22 Oct | 3.81% | 5.13% |
| Wed 21 Oct | 5.49% | 5.99% |
| Tue 20 Oct | 4.35% | 4.72% |
| Mon 19 Oct | 3.89% | 3.54% |
| Sun 18 Oct | 5.07% | 3.63% |
| Sat 17 Oct | 3.46% | 5.07% |
| Fri 16 Oct | 3.04% | 3.01% |

Full detail per LDZ in [scores.csv](scores.csv).
