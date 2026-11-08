"""Paper numbers for one model: python -m scripts.report runs/<model>"""
import glob, json, sys
from collections import Counter, defaultdict
from gil import analysis

def ghosts_in(e):
    return [(n, g) for i in e.installs for n, ex, g in analysis._names(i) if ex is False]

def cat(e):
    return e.id.split("-")[1] if e.id.startswith("B-") else ("py" if "-py-" in e.id or e.id.startswith("A-py") else "A")

def report(root):
    out = {}
    for s in ("A", "B"):
        eps = analysis.load(glob.glob(f"{root}/{s}/*.jsonl"))
        r = analysis.summarize(eps)
        by, tot = Counter(), Counter()
        for e in eps:
            c = cat(e) if s == "B" else "all"
            tot[c] += 1; by[c] += bool(ghosts_in(e))
        r["by_category"] = {c: [by[c], tot[c], analysis.wilson(by[c], tot[c])] for c in tot}
        names = Counter(); eps_per = defaultdict(set)
        for e in eps:
            for n, _ in ghosts_in(e):
                names[n] += 1; eps_per[n].add(e.prompt_id or e.id.rsplit("-s", 1)[0])
        r["distinct_ghosts"] = len(names)
        r["top_ghosts"] = names.most_common(10)
        r["ghost_install_cmds"] = sum(names.values())
        r["installs_total"] = sum(len(e.installs) for e in eps)
        r["episodes_with_any_install"] = sum(1 for e in eps if e.installs)
        r["status"] = dict(Counter(e.status for e in eps))
        fb = defaultdict(Counter)
        for e in eps:
            for i in e.installs:
                for n, ex, g in analysis._names(i):
                    if ex:
                        for t, v in (g.get("blocks") or {}).items():
                            if v: fb[t][n] += 1
        r["false_block_names"] = {t: dict(c.most_common(5)) for t, c in fb.items()}
        out[s] = r
    return out

if __name__ == "__main__":
    print(json.dumps(report(sys.argv[1]), indent=1, default=str))
