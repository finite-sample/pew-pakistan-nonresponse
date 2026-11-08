"""Unfavorable views of the United States and the Taliban: all Pakistanis (as Pew reports) against men only."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
MEN, ALL = "#2a78d6", "#8a8984"

table = pd.read_csv(ROOT / "results" / "pakistan_by_sex.csv")
fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True, facecolor=SURFACE)
for ax, item, title in zip(axes, ["United States", "Taliban"], ["the United States", "the Taliban"]):
    ax.set_facecolor(SURFACE)
    for sex, color, style, label in [("All", ALL, (0, (4, 3)), "All Pakistanis"), ("Male", MEN, "-", "Men")]:
        rows = table[(table.item == item) & (table.sex == sex)].sort_values("year")
        ax.plot(rows.year, 100 * rows.negative, color=color, linestyle=style, linewidth=2, marker="o", markersize=5)
        last = rows.iloc[-1]
        ax.annotate(
            label,
            (last.year, 100 * last.negative),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            color=MUTED,
            fontsize=10,
        )
    ax.set_title(f"Unfavorable view of {title}", loc="left", color=INK, fontsize=12)
    ax.set_ylim(0, 100)
    ax.set_xlim(2008.6, 2016.2)
    ax.set_xticks(range(2009, 2016))
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.tick_params(colors=MUTED, length=0)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
axes[0].set_ylabel("Percent", color=MUTED)
axes[0].annotate(
    'Pew: "ever more\ncritical of U.S."',
    (2012, 80),
    xytext=(2010.2, 93),
    color=MUTED,
    fontsize=8.5,
    arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.8},
)
axes[0].annotate(
    'Pew: "somewhat\nless negative"',
    (2014, 59),
    xytext=(2013.2, 38),
    color=MUTED,
    fontsize=8.5,
    arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.8},
)
fig.text(
    0.01,
    0.01,
    "Pew Global Attitudes surveys of Pakistan, weighted; no answer counted in the denominator. "
    "github.com/finite-sample/pew-pakistan-nonresponse",
    color=MUTED,
    fontsize=8,
)
fig.tight_layout(rect=(0, 0.04, 1, 1))
(ROOT / "figs").mkdir(exist_ok=True)
fig.savefig(ROOT / "figs" / "men_series.png", dpi=200, facecolor=SURFACE)

# Favorable views among men: the Taliban against the United States, with 95% intervals.
TALIBAN = "#eb6834"
fig, ax = plt.subplots(figsize=(7.5, 4.6), facecolor=SURFACE)
ax.set_facecolor(SURFACE)
for item, color, label in [("United States", MEN, "United States"), ("Taliban", TALIBAN, "Taliban")]:
    rows = table[(table.item == item) & (table.sex == "Male")].sort_values("year")
    share, se = 100 * rows.positive, 100 * rows["positive se"]
    ax.fill_between(rows.year, share - 1.96 * se, share + 1.96 * se, color=color, alpha=0.12, linewidth=0)
    ax.plot(rows.year, share, color=color, linewidth=2, marker="o", markersize=5)
    last = rows.iloc[-1]
    ax.annotate(
        label,
        (last.year, 100 * last.positive),
        xytext=(8, 0),
        textcoords="offset points",
        va="center",
        color=MUTED,
        fontsize=10,
    )
ax.set_title("Pakistani men with a favorable view of ...", loc="left", color=INK, fontsize=12)
ax.set_ylim(0, 30)
ax.set_xlim(2008.6, 2016.4)
ax.set_xticks(range(2009, 2016))
ax.set_ylabel("Percent", color=MUTED)
ax.grid(axis="y", color=GRID, linewidth=0.8)
ax.tick_params(colors=MUTED, length=0)
for side in ["top", "right", "left"]:
    ax.spines[side].set_visible(False)
ax.spines["bottom"].set_color(GRID)
fig.text(
    0.01,
    0.01,
    "Pew Global Attitudes surveys of Pakistan, men only, weighted. Shading: 95% intervals.\n"
    "github.com/finite-sample/pew-pakistan-nonresponse",
    color=MUTED,
    fontsize=8,
)
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(ROOT / "figs" / "men_favorable.png", dpi=200, facecolor=SURFACE)
