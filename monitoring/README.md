# Live track record

Day-ahead forecasts issued daily by the champion model (`.github/workflows/daily-forecast.yml`), scored against quality-checked actuals. Last 28 days with actuals: 16 Oct to 26 Oct 2026 (11 gas days, 141 LDZ-days scored).

| | MAPE |
| --- | --- |
| Model | 4.86% |
| National Gas day-ahead | 5.17% |

P10-P90 range coverage: 87% (target 80%).

No drift: the model is level with or ahead of the benchmark.

## By gas day

| Gas day | Model MAPE | National Gas MAPE |
| --- | --- | --- |
| Mon 26 Oct | 6.75% | nan% |
| Sun 25 Oct | 3.47% | 3.92% |
| Sat 24 Oct | 10.95% | 12.99% |
| Fri 23 Oct | 4.42% | 3.24% |
| Thu 22 Oct | 3.81% | 5.13% |
| Wed 21 Oct | 5.48% | 6.07% |
| Tue 20 Oct | 4.32% | 4.55% |
| Mon 19 Oct | 4.32% | 3.97% |
| Sun 18 Oct | 5.05% | 3.61% |
| Sat 17 Oct | 3.46% | 5.07% |
| Fri 16 Oct | 3.04% | 3.01% |

Full detail per LDZ in [scores.csv](scores.csv).
