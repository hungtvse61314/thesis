"""Result charts for Chapter 4 (Figures 4.2, 4.5, 4.6, 4.9), drawn from the
JSON outputs of run_revision.py and run_battery.py.

Usage:  .venv/bin/python -m experiments.plot_results <output-dir>
"""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#1f1f1e", "#6b6a63", "#e4e3dd"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "axes.titlesize": 9.5,
    "axes.titleweight": "bold",
    "xtick.color": MUTED,
    "ytick.color": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "legend.frameon": False,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

MODELS = ["M1", "M2", "M3", "M4", "M5", "M6", "M6-orig"]
LABELS = {
    "M1": "M1 TF–IDF", "M2": "M2 SBERT", "M3": "M3 Section SBERT", "M4": "M4 Requirement",
    "M5": "M5 + seniority", "M6": "M6 Full (revised)", "M6-orig": "M6 Full (original)",
}
BASELINES = {"M1", "M2", "M3"}


def rank_axis(ax):
    ax.set_xscale("log")
    ax.set_xlim(5000, 0.7)
    ax.set_xticks([1, 10, 100, 1000])
    ax.set_xticklabels(["1", "10", "100", "1,000"])
    ax.minorticks_off()
    ax.grid(axis="y", visible=False)


def load(name):
    with open(os.path.join(HERE, "results", name)) as f:
        return json.load(f)


def ranking_effectiveness(rev, out):
    metrics = [("ndcg@5", "NDCG@5"), ("ndcg@10", "NDCG@10"), ("map", "MAP"),
               ("mrr", "MRR"), ("recall@10", "Recall@10"), ("recall@20", "Recall@20")]
    fig, axes = plt.subplots(2, 3, figsize=(6.3, 4.4), sharey=True)
    ys = list(range(len(MODELS)))[::-1]
    for ax, (key, title) in zip(axes.flat, metrics):
        for y, m in zip(ys, MODELS):
            v = rev["models"][m]["test_macro"][key]
            color = BLUE if m in BASELINES else ORANGE
            hollow = m == "M6-orig"
            ax.plot([0, v], [y, y], color=color, linewidth=2, solid_capstyle="round", alpha=0.35)
            ax.scatter([v], [y], s=34, zorder=3, color="white" if hollow else color,
                       edgecolors=color, linewidths=1.6)
            ax.text(v + 0.03, y, f"{v:.2f}", va="center", fontsize=7, color=INK)
        ax.set_xlim(0, 1.18)
        ax.set_xticks([0, 0.5, 1.0])
        ax.set_title(title, loc="left")
        ax.grid(axis="y", visible=False)
    for ax in axes[:, 0]:
        ax.set_yticks(ys)
        ax.set_yticklabels([LABELS[m] for m in MODELS])
    handles = [
        plt.Line2D([], [], marker="o", color=BLUE, linestyle="", label="Similarity-only baselines"),
        plt.Line2D([], [], marker="o", color=ORANGE, linestyle="", label="Requirement-decomposition models"),
        plt.Line2D([], [], marker="o", markerfacecolor="white", markeredgecolor=ORANGE, color=ORANGE,
                   linestyle="", label="Original configuration"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.04), fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(out, "fig_4_5_ranking_effectiveness.png"))
    plt.close(fig)


def robustness(bat, out):
    case = {c["jd_id"]: c for c in bat["cases"]}
    methods = ["tfidf", "sbert_full", "section_sbert", "requirement_aware", "requirement_seniority", "full"]
    names = ["M1", "M2", "M3", "M4", "M5", "M6"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.3, 2.9), sharey=True)
    ys = list(range(len(methods)))[::-1]
    sen = case[56]["ranks"]["revised"]
    for y, m in zip(ys, methods):
        s, f = sen[m]["senior"], sen[m]["fresher"]
        a1.plot([s, f], [y, y], color=GRID, linewidth=2, zorder=1)
        a1.scatter([s], [y], color=BLUE, s=32, zorder=3, marker="o")
        a1.scatter([f], [y], color=ORANGE, s=32, zorder=3, marker="s")
    a1.set_title("Seniority mismatch: rank of each CV", loc="left")
    a1.legend(handles=[
        plt.Line2D([], [], marker="o", color=BLUE, linestyle="", label="Senior CV"),
        plt.Line2D([], [], marker="s", color=ORANGE, linestyle="", label="Fresher CV"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=7.5)
    stf = case[51]["ranks"]["revised"]
    for y, m in zip(ys, methods):
        r = stf[m]
        lo, hi = min(r.values()), max(r.values())
        a2.plot([lo, hi], [y, y], color=GRID, linewidth=2, zorder=1)
        a2.scatter([r["original"]], [y], color=BLUE, s=32, zorder=3, marker="o")
        a2.scatter([r["stuffed"]], [y], color=ORANGE, s=32, zorder=4, marker="s")
        a2.scatter([r["supported"]], [y], color=AQUA, s=34, zorder=5, marker="^")
    a2.set_title("Keyword stuffing: rank of each version", loc="left")
    a2.legend(handles=[
        plt.Line2D([], [], marker="o", color=BLUE, linestyle="", label="Original"),
        plt.Line2D([], [], marker="s", color=ORANGE, linestyle="", label="Stuffed"),
        plt.Line2D([], [], marker="^", color=AQUA, linestyle="", label="Evidence-supported"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, fontsize=7.5, columnspacing=0.8)
    for ax in (a1, a2):
        rank_axis(ax)
    fig.supxlabel("Rank in the 4,013-CV corpus (log scale; better ranks to the right)", fontsize=8, y=-0.02)
    a1.set_yticks(ys)
    a1.set_yticklabels(names)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_4_6_robustness.png"))
    plt.close(fig)


def case_studies(bat, out):
    case = {c["jd_id"]: c for c in bat["cases"]}
    panels = [
        ("Seniority mismatch", 56, [("senior", "Senior"), ("fresher", "Fresher")]),
        ("Keyword stuffing", 51, [("original", "Original"), ("stuffed", "Stuffed"), ("supported", "Evidence-supported")]),
        ("Missing mandatory skill", 57, [("has_all", "Has all skills"), ("missing", "Missing PostgreSQL")]),
        ("Role confusion", 58, [("genuine", "Genuine developer"), ("confused", "Project manager")]),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(6.3, 4.0))
    for ax, (title, jd, roles) in zip(axes.flat, panels):
        r = case[jd]["ranks"]["revised"]
        ys = list(range(len(roles)))[::-1]
        for y, (key, label) in zip(ys, roles):
            b, p = r["sbert_full"][key], r["full"][key]
            ax.plot([b, p], [y, y], color=GRID, linewidth=2, zorder=1)
            ax.scatter([b], [y], color=BLUE, s=32, zorder=3, marker="o")
            ax.scatter([p], [y], color=ORANGE, s=32, zorder=3, marker="s")
        ax.set_yticks(ys)
        ax.set_yticklabels([lbl for _, lbl in roles])
        ax.set_ylim(-0.6, len(roles) - 0.4)
        rank_axis(ax)
        ax.set_title(title, loc="left")
    fig.supxlabel("Rank in the 4,013-CV corpus (log scale; better ranks to the right)", fontsize=8, y=0.06)
    fig.legend(handles=[
        plt.Line2D([], [], marker="o", color=BLUE, linestyle="", label="M2 SBERT full text"),
        plt.Line2D([], [], marker="s", color=ORANGE, linestyle="", label="M6 Full model (revised)"),
    ], loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.03), fontsize=8)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(os.path.join(out, "fig_4_9_case_studies.png"))
    plt.close(fig)


def dataset(rev, out):
    snap = rev["snapshot"]
    rows = [
        ("Ranking corpus\n(4,013 CVs)", [("Real", snap["real"]), ("Synthetic", 1000), ("Robustness battery", 27)]),
        ("Labeled pool\n(246 pairs)", [("Real", 138), ("Synthetic", 108)]),
    ]
    colors = {"Real": BLUE, "Synthetic": ORANGE, "Robustness battery": AQUA}
    fig, axes = plt.subplots(2, 1, figsize=(6.3, 1.9))
    for ax, (label, parts) in zip(axes, rows):
        total = sum(v for _, v in parts)
        left = 0.0
        for name, v in parts:
            w = v / total * 100
            ax.barh([0], [w - 0.4], left=left, color=colors[name], height=0.6)
            if w > 6:
                ax.text(left + w / 2, 0, f"{name}\n{v:,} ({w:.1f}%)", ha="center", va="center",
                        color="white", fontsize=7.5, fontweight="bold")
            left += w
        ax.set_xlim(0, 100)
        ax.set_yticks([0])
        ax.set_yticklabels([label])
        ax.set_xticks([])
        ax.grid(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_visible(False)
    axes[0].text(100, 0.42, "Robustness battery: 27 (0.7%)", ha="right", fontsize=7, color=MUTED)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_4_2_dataset_composition.png"))
    plt.close(fig)


def performance(lat, out):
    # Per-document stage costs come from the ingestion benchmark (Table 4.16);
    # ranking latency from run_latency.py.
    stages = [("Text-layer extraction", 0.015), ("Parsing and indexing", 0.0023), ("OCR (per page)", 8.08)]
    order = ["tfidf", "sbert_full", "section_sbert", "requirement_aware", "requirement_seniority", "full"]
    names = ["M1 TF–IDF", "M2 SBERT", "M3 Section SBERT", "M4 Requirement", "M5 + seniority", "M6 Full (revised)"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.3, 2.6), gridspec_kw={"width_ratios": [1, 1.25]})
    ys = list(range(len(stages)))[::-1]
    for y, (name, v) in zip(ys, stages):
        a1.barh([y], [v], color=BLUE, height=0.55)
        a1.text(v * 1.25, y, f"{v * 1000:.1f} ms" if v < 1 else f"{v:.2f} s", va="center", fontsize=7.5)
    a1.set_yticks(ys)
    a1.set_yticklabels([n for n, _ in stages])
    a1.set_title("Per-document pipeline cost", loc="left")
    ys = list(range(len(order)))[::-1]
    for y, m in zip(ys, order):
        v = lat["per_method"][m]["mean_seconds"]
        color = BLUE if m in ("tfidf", "sbert_full", "section_sbert") else ORANGE
        a2.barh([y], [v], color=color, height=0.55)
        a2.text(v * 1.25, y, f"{v:.2f} s", va="center", fontsize=7.5)
    a2.set_yticks(ys)
    a2.set_yticklabels(names)
    a2.set_title("Ranking latency per JD (4,013 CVs)", loc="left")
    for ax in (a1, a2):
        ax.set_xscale("log")
        ax.grid(axis="y", visible=False)
        ax.set_xlabel("Seconds (log scale)")
    a1.set_xlim(0.001, 100)
    a2.set_xlim(0.05, 300)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_4_8_performance.png"))
    plt.close(fig)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    rev, bat = load("revision_results.json"), load("battery_results.json")
    ranking_effectiveness(rev, out)
    robustness(bat, out)
    case_studies(bat, out)
    dataset(rev, out)
    if os.path.exists(os.path.join(HERE, "results", "latency_results.json")):
        performance(load("latency_results.json"), out)
    print("saved to", out)


if __name__ == "__main__":
    main()
