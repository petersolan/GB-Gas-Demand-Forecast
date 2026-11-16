# Live track record

Day-ahead forecasts issued daily by the champion model (`.github/workflows/daily-forecast.yml`), scored against quality-checked actuals. Last 28 days with actuals: 19 Oct to 15 Nov 2026 (20 gas days, 260 LDZ-days scored).

| | MAPE |
| --- | --- |
| Model | 5.45% |
| National Gas day-ahead | 5.79% |

P10-P90 range coverage: 80% (target 80%).

No drift: the model is level with or ahead of the benchmark.

## By gas day

| Gas day | Model MAPE | National Gas MAPE |
| --- | --- | --- |
| Sun 15 Nov | 3.86% | 2.94% |
| Sat 14 Nov | 3.69% | 4.41% |
| Fri 13 Nov | 3.67% | 4.84% |
| Wed 11 Nov | 2.56% | 3.22% |
| Tue 10 Nov | 4.75% | 5.69% |
| Mon 09 Nov | 6.53% | 6.25% |
| Sun 08 Nov | 4.53% | 3.21% |
| Sat 31 Oct | 3.17% | 3.98% |
| Fri 30 Oct | 4.05% | 4.68% |
| Thu 29 Oct | 4.39% | 3.30% |
| Wed 28 Oct | 12.57% | 10.62% |
| Tue 27 Oct | 13.22% | 16.87% |
| Mon 26 Oct | 6.76% | nan% |
| Sun 25 Oct | 3.45% | 3.90% |

Full detail per LDZ in [scores.csv](scores.csv).
