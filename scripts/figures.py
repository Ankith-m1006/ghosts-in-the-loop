"""Paper figures from runs/<model>-report.json: python -m scripts.figures e4b g31b"""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LABEL = {"e4b": "Gemma 4 E4B", "g31b": "Gemma 4 31B (FP8)"}
COL = {"e4b": "#9e9e9e", "g31b": "#111111"}
TRIG = [("A", "all", "Natural\n(Set A)"), ("B", "longtail", "Long-tail"), ("B", "misspelled", "Misspelled\nreal name"),
        ("B", "time", "\"Released\nin 2026\""), ("B", "invented", "Task names a\nmissing library")]
REC = [("switched_real", "switched to a real package"), ("wrote_it", "wrote it / stand-in"),
       ("second_ghost", "another invented name"), ("git_or_url", "git or URL"), ("gave_up", "gave up")]

def main(models):
    out = Path("../paper/figures"); out.mkdir(parents=True, exist_ok=True)
    reps = {m: json.load(open(f"runs/{m}-report.json")) for m in models}
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    # Figure 2: share of episodes with a ghost install, by trigger, with 95% Wilson intervals
    fig, ax = plt.subplots(figsize=(8, 3.6)); w = 0.8 / len(models)
    for k, m in enumerate(models):
        xs, ys, lo, hi = [], [], [], []
        for j, (s, c, _) in enumerate(TRIG):
            hit, tot, (p, l, h) = reps[m][s]["by_category"][c]
            xs.append(j + (k - (len(models) - 1) / 2) * w); ys.append(100 * p); lo.append(100 * (p - l)); hi.append(100 * (h - p))
        ax.bar(xs, ys, w * 0.9, color=COL[m], label=LABEL[m], yerr=[lo, hi], capsize=3, ecolor="#555")
    ax.set_xticks(range(len(TRIG))); ax.set_xticklabels([t[2] for t in TRIG])
    ax.set_ylabel("% of episodes with a\nghost install attempt"); ax.set_ylim(0, 100); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(out / "fig2-ghost-rate-by-trigger.png", dpi=200); plt.close(fig)
    # Figure 3: what the agent did after the first failed ghost install (Set B)
    fig, ax = plt.subplots(figsize=(8, 1.2 + 0.7 * len(models)))
    greys = ["#111", "#777", "#b5b5b5", "#d9d9d9", "#efefef"]
    for k, m in enumerate(models):
        rec = reps[m]["B"]["recovery"]; tot = sum(rec.values()) or 1; left = 0
        for (key, lab), g in zip(REC, greys):
            v = 100 * rec.get(key, 0) / tot
            ax.barh(k, v, left=left, color=g, edgecolor="white", label=lab if k == 0 else None)
            if v >= 6: ax.text(left + v / 2, k, f"{v:.0f}%", ha="center", va="center", color="white" if g in ("#111", "#777") else "#111", fontsize=9)
            left += v
    ax.set_yticks(range(len(models))); ax.set_yticklabels([f"{LABEL[m]}\n(n={sum(reps[m]['B']['recovery'].values())})" for m in models])
    ax.set_xlim(0, 100); ax.set_xlabel("% of Set B episodes with a ghost install"); ax.invert_yaxis()
    ax.legend(ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.02), loc="lower center", fontsize=9)
    fig.tight_layout(); fig.savefig(out / "fig3-recovery.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    print("saved", sorted(p.name for p in out.glob("*.png")))

if __name__ == "__main__":
    main(sys.argv[1:] or ["e4b"])
