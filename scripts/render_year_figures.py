#!/usr/bin/env python3
"""Render 365-day Congress Signal Lab diagnostic figures from derived year-data.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

COLORS = {
    "consensus_20cap": "#0b2e59",  # Navy
    "tfidf_20cap": "#0d9488",      # Teal
    "freshness_20cap": "#d97706",  # Orange
    "SPY": "#64748b",              # Slate
}
LABELS = {
    "consensus_20cap": "TF-IDF + Consensus (20% cap)",
    "tfidf_20cap": "TF-IDF (20% cap)",
    "freshness_20cap": "Freshness (20% cap)",
    "SPY": "SPY Buy & Hold",
}
ORDER = ["consensus_20cap", "tfidf_20cap", "freshness_20cap", "SPY"]


def _to_pct(val: float) -> float:
    v = float(val)
    return v * 100.0


def _extract_nav(data: dict) -> tuple[list[str], dict[str, np.ndarray]]:
    nav_block = data["nav"]
    dates = data.get("dates") or nav_block.get("dates")
    series: dict[str, np.ndarray] = {}
    for k in ORDER:
        raw = nav_block[k]
        if isinstance(raw, dict):
            if not dates:
                dates = sorted(raw.keys())
            series[k] = np.array([float(raw[d]) for d in dates], dtype=float)
        else:
            series[k] = np.array(raw, dtype=float)
    return list(dates), series


def _extract_monthly(data: dict) -> tuple[list[str], np.ndarray]:
    m_block = data["metrics"]
    sample = m_block["consensus_20cap"]["monthly_returns"]
    months = list(sample.keys()) if isinstance(sample, dict) else [x["month"] for x in sample]
    mat = []
    for k in ORDER:
        mr = m_block[k]["monthly_returns"]
        vals = [float(mr[m]) for m in months] if isinstance(mr, dict) else [float(x["value"]) for x in mr]
        mat.append(vals)
    arr = np.array(mat, dtype=float)
    arr = arr * 100.0
    return months, arr


def _save_both(fig: plt.Figure, out_dir: Path, stem: str) -> None:
    fig.savefig(out_dir / f"{stem}.png", dpi=100, facecolor="white")
    fig.savefig(out_dir / f"{stem}.svg", facecolor="white", metadata={"Date": None})
    plt.close(fig)


def render_equity(data: dict, out_dir: Path, footer: str) -> None:
    dates_str, navs = _extract_nav(data)
    x_dates = mdates.datestr2num(dates_str)
    metrics = data["metrics"]
    fig, (ax_nav, ax_dd) = plt.subplots(
        2, 1, figsize=(16, 9.6), dpi=100, sharex=True, gridspec_kw={"height_ratios": [1.65, 1.0], "hspace": 0.14}
    )
    fig.patch.set_facecolor("white")
    fig.suptitle(
        "365-Day Portfolio Trajectory & Daily Drawdown (Initial Capital = 100.0)",
        fontsize=18, fontweight="bold", color="#0f172a", y=0.955,
    )
    ax_nav.set_title(
        "251 trading sessions · Initial capital = 100 · Net of modeled trading costs",
        fontsize=12.5, color="#475569", pad=10,
    )
    ax_nav.axhline(100.0, color="#cbd5e1", linestyle="--", linewidth=1.2, zorder=1)
    ax_dd.axhline(0.0, color="#cbd5e1", linestyle="-", linewidth=1.0, zorder=1)

    for k in ORDER:
        nav_arr = navs[k]
        peaks = np.maximum.accumulate(np.concatenate([[100.0], nav_arr]))[1:]
        dd_pct = (nav_arr / peaks - 1.0) * 100.0
        tot_ret = _to_pct(metrics[k]["total_return"])
        max_dd = abs(_to_pct(metrics[k]["max_drawdown"]))
        lw = 2.8 if k == "consensus_20cap" else 2.0
        z = 5 if k == "consensus_20cap" else 3
        lbl = f"{LABELS[k]}  (Net {tot_ret:+.2f}% | Max DD -{max_dd:.2f}%)"
        ax_nav.plot(x_dates, nav_arr, label=lbl, color=COLORS[k], linewidth=lw, zorder=z)
        ax_dd.plot(x_dates, dd_pct, color=COLORS[k], linewidth=lw - 0.3, zorder=z)
        if k == "consensus_20cap":
            ax_dd.fill_between(x_dates, dd_pct, 0.0, color=COLORS[k], alpha=0.10, zorder=2)

    ax_nav.set_ylabel("Normalized NAV (Initial = 100)", fontsize=12, fontweight="bold", color="#1e293b")
    ax_dd.set_ylabel("Daily Drawdown (%)", fontsize=12, fontweight="bold", color="#1e293b")
    ax_nav.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#e2e8f0", fontsize=11.5)
    for ax in (ax_nav, ax_dd):
        ax.grid(True, linestyle=":", linewidth=0.8, color="#e2e8f0")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(labelsize=11, colors="#334155")
    ax_dd.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax_dd.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.12)
    fig.text(0.07, 0.03, footer, fontsize=10, color="#475569")
    _save_both(fig, out_dir, "equity")


def render_monthly(data: dict, out_dir: Path, footer: str) -> None:
    months, mat = _extract_monthly(data)
    x_labels = [f"{m}\n(partial)" if i in (0, len(months) - 1) else m for i, m in enumerate(months)]
    y_labels = [LABELS[k] for k in ORDER]

    fig, ax = plt.subplots(figsize=(16, 6.8), dpi=100)
    fig.patch.set_facecolor("white")
    fig.suptitle(
        "Monthly Net Return Schedule (%) Across Strategies & Benchmark",
        fontsize=18, fontweight="bold", color="#0f172a", y=0.94,
    )
    ax.set_title(
        "2025-11 (from Nov 7) and 2026-11 (through Nov 6) are partial calendar months",
        fontsize=12, color="#475569", pad=14,
    )
    cmap = LinearSegmentedColormap.from_list("navy_teal_div", ["#b45309", "#fef3c7", "#ffffff", "#ccfbf1", "#0b2e59"])
    bound = max(abs(float(np.min(mat))), abs(float(np.max(mat))), 5.0)
    norm = TwoSlopeNorm(vmin=-bound, vcenter=0.0, vmax=bound)
    im = ax.imshow(mat, cmap=cmap, norm=norm, aspect="auto")

    ax.set_xticks(np.arange(len(x_labels)), labels=x_labels, fontsize=10.5, fontweight="bold", color="#1e293b")
    ax.set_yticks(np.arange(len(y_labels)), labels=y_labels, fontsize=11.5, fontweight="bold", color="#1e293b")
    for r in range(mat.shape[0]):
        for c in range(mat.shape[1]):
            v = mat[r, c]
            txt_color = "white" if abs(v) > bound * 0.58 else "#0f172a"
            ax.text(c, r, f"{v:+.2f}%", ha="center", va="center", fontsize=10.5, fontweight="bold", color=txt_color)

    cbar = fig.colorbar(im, ax=ax, fraction=0.022, pad=0.02)
    cbar.ax.tick_params(labelsize=10.5)
    cbar.set_label("Monthly Return (%)", fontsize=11, color="#1e293b")
    fig.subplots_adjust(left=0.20, right=0.94, top=0.80, bottom=0.18)
    fig.text(0.06, 0.04, footer, fontsize=10, color="#475569")
    _save_both(fig, out_dir, "monthly")


def render_drivers(data: dict, out_dir: Path, footer: str) -> None:
    fig, (ax_attr, ax_cap) = plt.subplots(1, 2, figsize=(16, 7.2), dpi=100, gridspec_kw={"wspace": 0.28})
    fig.patch.set_facecolor("white")
    fig.suptitle(
        "Return Concentration & Capital-Allocation Sensitivity",
        fontsize=18, fontweight="bold", color="#0f172a", y=0.95,
    )
    contrib = data["consensus_contribution_pp"]
    labels = ["Other positions\n(net)" if "other" in c["label"].lower() else c["label"] for c in contrib][::-1]
    vals = [float(c["value"]) for c in contrib][::-1]
    bar_colors = ["#64748b" if "other" in lbl.lower() else "#0b2e59" for lbl in labels]
    y_pos = np.arange(len(labels))
    bars = ax_attr.barh(y_pos, vals, color=bar_colors, height=0.55)
    ax_attr.set_yticks(y_pos, labels=labels, fontsize=11.5, fontweight="bold", color="#1e293b")
    ax_attr.set_xlabel(f"Contribution to {sum(vals):+.2f}% total return (pp)", fontsize=11.5, fontweight="bold")
    ax_attr.set_title(f"Top 3 positions: {sum(float(c['value']) for c in contrib if 'other' not in c['label'].lower()) / sum(vals) * 100:.1f}% of net profit", fontsize=12, color="#334155", pad=10)
    ax_attr.set_xlim(0, max(vals) * 1.25)
    for b, v in zip(bars, vals):
        ax_attr.text(v + 0.3, b.get_y() + b.get_height() / 2, f"+{v:.2f} pp", va="center", fontsize=11, fontweight="bold", color="#0f172a")

    cap_block = data["capital_sensitivity"]
    strat_keys = ["freshness", "tfidf", "consensus"]
    strat_names = ["Freshness", "TF-IDF", "TF-IDF + Consensus"]
    v2 = [_to_pct(cap_block[k]["2"]) for k in strat_keys]
    v20 = [_to_pct(cap_block[k]["20"]) for k in strat_keys]
    x = np.arange(len(strat_names))
    w = 0.35
    b1 = ax_cap.bar(x - w / 2, v2, w, label="2% Initial-Capital Cap / Cohort", color="#94a3b8")
    b2 = ax_cap.bar(x + w / 2, v20, w, label="20% Initial-Capital Cap / Cohort", color="#0d9488")
    ax_cap.set_xticks(x, labels=strat_names, fontsize=11.5, fontweight="bold", color="#1e293b")
    ax_cap.set_ylabel("365-Day Cumulative Net Return (%)", fontsize=11.5, fontweight="bold")
    ax_cap.set_title("Per-cohort budget · Cash constrained · No borrowing", fontsize=12, color="#334155", pad=10)
    ax_cap.set_ylim(0, max(v20) * 1.22)
    ax_cap.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#e2e8f0", fontsize=11)
    for b in list(b1) + list(b2):
        h = b.get_height()
        ax_cap.text(b.get_x() + b.get_width() / 2, h + 0.6, f"+{h:.2f}%", ha="center", fontsize=10.5, fontweight="bold", color="#0f172a")

    for ax in (ax_attr, ax_cap):
        ax.grid(True, linestyle=":", linewidth=0.8, color="#e2e8f0")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(labelsize=11, colors="#334155")
    fig.subplots_adjust(left=0.12, right=0.96, top=0.82, bottom=0.17)
    fig.text(0.06, 0.035, "Attribution subtracts PnL; it is not a strategy rerun.\n" + footer, fontsize=10, color="#475569")
    _save_both(fig, out_dir, "drivers")


def main() -> None:
    in_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("assets/research/year-data.json")
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("assets/research/year")
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams["svg.hashsalt"] = "congress-signal-lab-year"
    data = json.loads(in_path.read_text(encoding="utf-8"))
    start, end = data.get("start", "2025-11-07"), data.get("end", "2026-11-06")
    footer = (
        f"Source: docs/HISTORICAL_STUDY.md & assets/research/year-data.json | Sample: {start} to {end} ({data.get('sessions', 251)} SPY sessions)\n"
        "Legacy diagnostic (not out-of-sample). Known TF-history and asset/execution defects; corrected rerun pending. See docs/AUDIT_365.md."
    )
    render_equity(data, out_dir, footer)
    render_monthly(data, out_dir, footer)
    render_drivers(data, out_dir, footer)


if __name__ == "__main__":
    main()
