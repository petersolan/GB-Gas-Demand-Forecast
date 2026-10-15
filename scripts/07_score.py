"""Score the live forecasts against the actuals published since, and check for drift.

Reads monitoring/forecasts.csv (scripts/06_forecast.py) and the archived National Gas data, writes
monitoring/scores.csv and monitoring/README.md (the live track record), and prints a GitHub Actions
warning when the model falls behind National Gas over the last four weeks.

    python scripts/07_score.py
"""

import os

import pandas as pd

from gasfc.config import MONITORING
from gasfc.monitoring import WINDOW_DAYS, drift, score, summary
from gasfc.nationalgas import build_daily

COLUMNS = ["gas_day", "ldz", "demand", "forecast", "p10", "p90", "ng_forecast_da", "ape_model", "ape_ng"]


def report(scores: pd.DataFrame, s: dict, warning: str | None) -> str:
    lines = ["# Live track record", ""]
    if s["days"] == 0:
        return "\n".join(lines + ["No forecasts with published actuals yet.", ""])
    lines += [
        f"Day-ahead forecasts issued daily by the champion model (`.github/workflows/daily-forecast.yml`), "
        f"scored against quality-checked actuals. Last {WINDOW_DAYS} days with actuals: "
        f"{s['first_day']:%d %b} to {s['last_day']:%d %b %Y} ({s['days']} gas days, 13 LDZs).",
        "",
        "| | MAPE |",
        "| --- | --- |",
        f"| Model | {s['mape_model']:.2f}% |",
        f"| National Gas day-ahead | {s['mape_ng']:.2f}% |",
        "",
        f"P10-P90 range coverage: {s['coverage']:.0%} (target 80%).",
        "",
        f"**Drift warning:** {warning}"
        if warning
        else "No drift: the model is level with or ahead of the benchmark.",
        "",
        "## By gas day",
        "",
        "| Gas day | Model MAPE | National Gas MAPE |",
        "| --- | --- | --- |",
    ]
    daily = scores.groupby("gas_day")[["ape_model", "ape_ng"]].mean().sort_index(ascending=False).head(14)
    lines += [f"| {d:%a %d %b} | {r.ape_model:.2f}% | {r.ape_ng:.2f}% |" for d, r in daily.iterrows()]
    lines += ["", "Full detail per LDZ in [scores.csv](scores.csv).", ""]
    return "\n".join(lines)


def main() -> None:
    forecasts = pd.read_csv(MONITORING / "forecasts.csv", parse_dates=["gas_day", "issued_at"])
    scores = score(forecasts, build_daily())
    out = scores[COLUMNS].copy()
    out["gas_day"] = out["gas_day"].dt.strftime("%Y-%m-%d")
    out.round(3).to_csv(MONITORING / "scores.csv", index=False)

    s = summary(scores)
    warning = drift(s)
    text = report(scores, s, warning)
    (MONITORING / "README.md").write_text(text, encoding="utf-8")
    print(text)
    if warning:
        print(f"::warning title=Forecast drift::{warning}")  # shown as an annotation on the Actions run
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main()
