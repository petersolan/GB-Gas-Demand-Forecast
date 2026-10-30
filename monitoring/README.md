# Live track record

Day-ahead forecasts issued daily by the champion model (`.github/workflows/daily-forecast.yml`), scored against quality-checked actuals. Last 28 days with actuals: 16 Oct to 29 Oct 2026 (14 gas days, 179 LDZ-days scored).

| | MAPE |
| --- | --- |
| Model | 6.08% |
| National Gas day-ahead | 6.38% |

P10-P90 range coverage: 79% (target 80%).

No drift: the model is level with or ahead of the benchmark.

## By gas day

| Gas day | Model MAPE | National Gas MAPE |
| --- | --- | --- |
| Thu 29 Oct | 4.37% | 3.28% |
| Wed 28 Oct | 12.67% | 10.73% |
| Tue 27 Oct | 13.24% | 16.89% |
| Mon 26 Oct | 6.75% | nan% |
| Sun 25 Oct | 3.47% | 3.92% |
| Sat 24 Oct | 10.95% | 12.99% |
| Fri 23 Oct | 4.32% | 3.34% |
| Thu 22 Oct | 3.79% | 5.15% |
| Wed 21 Oct | 5.48% | 6.07% |
| Tue 20 Oct | 4.32% | 4.55% |
| Mon 19 Oct | 4.32% | 3.97% |
| Sun 18 Oct | 5.14% | 3.31% |
| Sat 17 Oct | 3.46% | 5.07% |
| Fri 16 Oct | 3.04% | 3.01% |

Full detail per LDZ in [scores.csv](scores.csv).
