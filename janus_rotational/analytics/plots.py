"""
Janus Rotational System — Academic Report Figures
==================================================
Four publication-quality matplotlib figures.

Figure 1 — Macro Regime Overlay
    SPY price chart with red fill_between shading marking every week
    where the Phase 1 crash_regime flag is True.

Figure 2 — Dynamic Capital Allocation
    100% stacked area chart: proportion of portfolio in Equities vs Bonds
    each day, showing the staggered 4-week transition into/out of crashes.

Figure 3 — Cumulative Equity Curves & Underwater Drawdown
    Top panel (log scale): Janus, SPY, 60/40 equity curves from $1M.
    Bottom panel: simultaneous underwater drawdown for all three.

Figure 4 — White's Reality Check Histogram
    Distribution of 500 naive Sharpe Ratios (bootstrap) with a dashed
    red line marking the Janus Sharpe.  p-value annotated on the chart.

All figures saved to the `plots/` directory at 200 dpi (report quality).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

from janus_rotational.analytics.metrics import drawdown_series

# ── Style constants ────────────────────────────────────────────────────────────
JANUS_COLOR  = "#1B263B"     # dark navy
SPY_COLOR    = "#E63946"     # vivid red
BENCH_COLOR  = "#457B9D"     # steel blue
CRASH_COLOR  = "#E63946"     # same red, lower alpha
US_EQ_COLOR  = "#1976D2"     # deep blue
INT_EQ_COLOR = "#388E3C"     # forest green
BOND_COLOR   = "#F57C00"     # dark orange
CASH_COLOR   = "#CFD8DC"     # blue-grey light

FONT_TITLE  = {"fontsize": 13, "fontweight": "bold"}
FONT_LABEL  = {"fontsize": 11}
FONT_TICK   = {"labelsize": 9}
FONT_LEGEND = {"fontsize": 9}

PLOT_DIR = Path(__file__).resolve().parents[2] / "plots"
PLOT_DIR.mkdir(exist_ok=True)

plt.rcParams.update({
    "figure.dpi":       100,
    "savefig.dpi":      200,
    "font.family":      "DejaVu Sans",
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "axes.grid":        True,
    "grid.alpha":       0.35,
    "grid.linestyle":   "--",
    "axes.axisbelow":   True,
})


# ─────────────────────────────────────────────────────────────────────────────
# Shared helper
# ─────────────────────────────────────────────────────────────────────────────

def _regime_fill(ax, daily_index: pd.DatetimeIndex, regime: pd.DataFrame) -> None:
    """
    Shade the x-axis background red on every day where crash_regime = True.
    Uses ax.fill_between with transform=ax.get_xaxis_transform() so the
    shading always spans the full y-axis regardless of scale.
    """
    is_crash = regime["crash_regime"].reindex(daily_index, method="ffill").fillna(False)
    ax.fill_between(
        daily_index,
        0, 1,
        where=is_crash.values,
        transform=ax.get_xaxis_transform(),
        color=CRASH_COLOR,
        alpha=0.12,
        linewidth=0,
        label="Crash Regime (Phase 1)",
        zorder=0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Figure 1 — Macro Regime Overlay
# ─────────────────────────────────────────────────────────────────────────────

def plot_regime_overlay(
    prices:  pd.DataFrame,
    regime:  pd.DataFrame,
    start:   str,
    end:     str,
    save:    bool = True,
    output_dir: Path | None = None,
    title_suffix: str = "",
    fig_num: int = 1,
) -> plt.Figure:
    """
    SPY total-return price chart with crash-regime red shading.
    """
    spy = prices.loc[start:end, "SPY"].dropna()

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.suptitle(
        f"Figure {fig_num} — SPY Price & Macro Regime Switch {title_suffix}",
        **FONT_TITLE, y=1.01,
    )

    _regime_fill(ax, spy.index, regime)

    ax.plot(spy.index, spy, color=SPY_COLOR, linewidth=1.4, zorder=2, label="SPY (adj. close)")
    ax.set_ylabel("Adjusted Close (USD)", **FONT_LABEL)
    ax.set_xlabel("")
    ax.tick_params(axis="both", **FONT_TICK)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())

    # Custom legend: SPY line + crash patch
    crash_patch = mpatches.Patch(color=CRASH_COLOR, alpha=0.35, label="Crash Regime (Phase 1)")
    ax.legend(handles=[ax.lines[0], crash_patch], **FONT_LEGEND, loc="upper left")

    # Annotate the 2020 COVID crash band
    ax.annotate(
        "COVID-19\n(May – Nov 2020)",
        xy=(pd.Timestamp("2020-08-01"), spy.loc["2020-08-01":"2020-08-07"].mean()),
        xytext=(pd.Timestamp("2021-06-01"), spy.loc["2021-05-28":"2021-06-04"].mean() * 0.65),
        arrowprops=dict(arrowstyle="->", color="grey", lw=1.2),
        fontsize=9, color="grey",
    )

    fig.tight_layout()
    if save:
        base_dir = output_dir if output_dir else PLOT_DIR
        base_dir.mkdir(exist_ok=True, parents=True)
        path = base_dir / f"figure_{fig_num}_regime_overlay.png"
        fig.savefig(path, bbox_inches="tight")
        print(f"  Saved → {path}")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Figure 2 — Dynamic Capital Allocation
# ─────────────────────────────────────────────────────────────────────────────

def plot_capital_allocation(
    daily: pd.DataFrame,
    regime: pd.DataFrame,
    save:   bool = True,
    output_dir: Path | None = None,
    title_suffix: str = "",
    fig_num: int = 2,
) -> plt.Figure:
    """
    100% stacked area chart of equity (US vs Int) vs bond vs cash allocation.
    """
    pv = daily["portfolio_value"].replace(0, np.nan)

    # Detect available granular columns
    us_val = daily["us_equity_value"] if "us_equity_value" in daily.columns else daily.get("equity_value", 0)
    gl_val = daily["global_equity_value"] if "global_equity_value" in daily.columns else 0
    bn_val = daily["bond_value"] if "bond_value" in daily.columns else 0

    us_pct   = (us_val / pv * 100).fillna(0)
    gl_pct   = (gl_val / pv * 100).fillna(0)
    bond_pct = (bn_val / pv * 100).fillna(0)
    cash_pct = (100 - us_pct - gl_pct - bond_pct).clip(lower=0)

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.suptitle(
        f"Figure {fig_num} — Granular Capital Allocation {title_suffix}",
        **FONT_TITLE, y=1.01,
    )

    ax.stackplot(
        daily.index,
        us_pct, gl_pct, bond_pct, cash_pct,
        labels=["US Equities", "Global Equities", "Bonds / Safe Haven", "Cash residual"],
        colors=[US_EQ_COLOR, INT_EQ_COLOR, BOND_COLOR, CASH_COLOR],
        alpha=0.85,
        zorder=2,
    )

    # Overlay crash regime boundary lines
    is_crash = regime["crash_regime"].reindex(daily.index, method="ffill").fillna(False)
    transitions = is_crash.astype(int).diff().fillna(0)
    for dt in transitions[transitions != 0].index:
        ax.axvline(dt, color="#333333", linestyle=":", linewidth=0.8, alpha=0.4, zorder=3)

    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_ylabel("% of Portfolio", **FONT_LABEL)
    ax.set_xlabel("")
    ax.tick_params(axis="both", **FONT_TICK)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.legend(loc="lower left", **FONT_LEGEND, frameon=True, framealpha=0.9)

    fig.tight_layout()
    if save:
        base_dir = output_dir if output_dir else PLOT_DIR
        base_dir.mkdir(exist_ok=True, parents=True)
        path = base_dir / f"figure_{fig_num}_capital_allocation.png"
        fig.savefig(path, bbox_inches="tight")
        print(f"  Saved → {path}")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Figure 3 — Equity Curves & Drawdown
# ─────────────────────────────────────────────────────────────────────────────

def plot_equity_and_drawdown(
    janus_curve:  pd.Series,
    spy_curve:    pd.Series,
    bench_curve:  pd.Series,
    regime:       pd.DataFrame,
    metrics_dict: dict,
    save:         bool = True,
    output_dir:   Path | None = None,
    title_suffix: str = "",
    fig_num:      int = 3,
) -> plt.Figure:
    """
    Top panel: log-scale equity curves (Janus vs SPY vs 60/40).
    Bottom panel: underwater drawdown for all three.
    """
    fig = plt.figure(figsize=(14, 9))
    gs  = fig.add_gridspec(2, 1, height_ratios=[3, 1.2], hspace=0.08)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)

    fig.suptitle(
        f"Figure {fig_num} — Equity Curves & Underwater Drawdown {title_suffix}",
        **FONT_TITLE,
    )

    # ── Top: equity curves (log scale) ───────────────────────────────────
    common_idx = janus_curve.index
    _regime_fill(ax1, common_idx, regime)

    for curve, color, label in [
        (janus_curve, JANUS_COLOR, "Janus Rotational"),
        (spy_curve,   SPY_COLOR,   "SPY (100%)"),
        (bench_curve, BENCH_COLOR, "60/40 ACWI/BND"),
    ]:
        c_aligned = curve.reindex(common_idx, method="ffill")
        ax1.semilogy(c_aligned.index, c_aligned, color=color, linewidth=1.6, label=label)

    # Annotate final values
    for curve, color, key in [
        (janus_curve, JANUS_COLOR, "janus"),
        (spy_curve,   SPY_COLOR,   "spy"),
        (bench_curve, BENCH_COLOR, "6040"),
    ]:
        m  = metrics_dict.get(key, {})
        lv = curve.iloc[-1]
        ax1.annotate(
            f"{m.get('cagr', 0)*100:+.1f}% CAGR\nSharpe {m.get('sharpe', 0):.2f}",
            xy=(curve.index[-1], lv),
            xytext=(-55, 0),
            textcoords="offset points",
            fontsize=8, color=color,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=color, alpha=0.85),
        )

    ax1.set_ylabel("Portfolio Value (log scale, USD)", **FONT_LABEL)
    ax1.yaxis.set_major_formatter(mtick.FuncFormatter(
        lambda x, _: f"${x/1e6:.1f}M" if x >= 1e6 else f"${x/1e3:.0f}K"
    ))
    ax1.legend(loc="upper left", **FONT_LEGEND)
    ax1.tick_params(axis="both", **FONT_TICK)
    plt.setp(ax1.get_xticklabels(), visible=False)

    # ── Bottom: drawdown ─────────────────────────────────────────────────
    _regime_fill(ax2, common_idx, regime)

    for curve, color, label, alpha in [
        (janus_curve, JANUS_COLOR, "Janus",       0.75),
        (spy_curve,   SPY_COLOR,   "SPY",          0.45),
        (bench_curve, BENCH_COLOR, "60/40",        0.45),
    ]:
        dd = drawdown_series(curve.reindex(common_idx, method="ffill")) * 100
        ax2.fill_between(dd.index, dd, 0, color=color, alpha=alpha, label=label, linewidth=0)
        ax2.plot(dd.index, dd, color=color, linewidth=0.6, alpha=0.9)

    ax2.set_ylabel("Drawdown (%)", **FONT_LABEL)
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax2.legend(loc="lower left", **FONT_LEGEND)
    ax2.tick_params(axis="both", **FONT_TICK)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.set_xlabel("")

    fig.tight_layout()
    if save:
        base_dir = output_dir if output_dir else PLOT_DIR
        base_dir.mkdir(exist_ok=True, parents=True)
        path = base_dir / f"figure_{fig_num}_equity_drawdown.png"
        fig.savefig(path, bbox_inches="tight")
        print(f"  Saved → {path}")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Figure 4 — White's Reality Check Histogram
# ─────────────────────────────────────────────────────────────────────────────

def plot_whites_test(
    whites_result: dict,
    save:          bool = True,
    output_dir:    Path | None = None,
    title_suffix:  str = "",
    fig_num:       int = 4,
) -> plt.Figure:
    """
    Histogram of naive Sharpe Ratios with the Janus Sharpe marked.
    """
    naive   = whites_result["naive_sharpes"]
    js      = whites_result["janus_sharpe"]
    p_val   = whites_result["p_value"]
    n_sims  = whites_result["n_sims"]

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle(
        f"Figure {fig_num} — White's Reality Check {title_suffix}",
        **FONT_TITLE, y=1.01,
    )

    # Histogram of naive Sharpes
    counts, bins, patches = ax.hist(
        naive, bins=35, density=True,
        color=BENCH_COLOR, alpha=0.70, edgecolor="white", linewidth=0.4,
        label=f"Naive strategies (N={n_sims})",
        zorder=2,
    )

    # Shade the tail: naive Sharpe >= Janus Sharpe
    for patch, left_edge in zip(patches, bins[:-1]):
        if left_edge >= js:
            patch.set_facecolor(CRASH_COLOR)
            patch.set_alpha(0.55)

    # Janus Sharpe vertical line
    ax.axvline(js, color=JANUS_COLOR, linewidth=2.2, linestyle="--", zorder=4,
               label=f"Janus Sharpe = {js:.3f}")

    # Normal-distribution overlay for the naive distribution
    x_range = np.linspace(naive.min() - 0.1, naive.max() + 0.1, 300)
    from scipy.stats import norm
    mu, sigma = naive.mean(), naive.std()
    ax.plot(x_range, norm.pdf(x_range, mu, sigma),
            color="dimgrey", linewidth=1.2, linestyle=":", label="Normal fit (naive)")

    # p-value annotation box
    significance = "Significant (α=0.05)" if p_val < 0.05 else "Not significant"
    ax.text(
        0.97, 0.95,
        f"p-value = {p_val:.4f}\n{significance}\n\n"
        f"Naive: μ={mu:.3f}, σ={sigma:.3f}\nNaive p95 = {np.percentile(naive, 95):.3f}",
        transform=ax.transAxes,
        fontsize=9, va="top", ha="right",
        bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="grey", alpha=0.9),
    )

    # Shade the p-value region with hatch
    ax.fill_betweenx(
        [0, counts.max() * 1.05],
        js, naive.max() + 0.2,
        alpha=0.08, color=CRASH_COLOR, zorder=1,
        label=f"p-value region ({p_val:.4f})",
    )

    ax.set_xlabel("Annualised Sharpe Ratio", **FONT_LABEL)
    ax.set_ylabel("Density", **FONT_LABEL)
    ax.tick_params(axis="both", **FONT_TICK)
    ax.legend(loc="upper left", **FONT_LEGEND)
    ax.set_xlim(naive.min() - 0.1, naive.max() + 0.2)

    fig.tight_layout()
    if save:
        base_dir = output_dir if output_dir else PLOT_DIR
        base_dir.mkdir(exist_ok=True, parents=True)
        path = base_dir / f"figure_{fig_num}_whites_reality_check.png"
        fig.savefig(path, bbox_inches="tight")
        print(f"  Saved → {path}")
    return fig
