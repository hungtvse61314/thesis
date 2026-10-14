"""Single-configuration re-run of the ranking-effectiveness experiment for the
thesis revision.

One frozen snapshot (raematch.db, all 4,013 CVs, the current JD requirement
lists) and one fixed development/test split are used for everything:
  1. the evidence thresholds of the revised model are calibrated on the
     development half only;
  2. M1-M6 (and M6 under the original configuration) are scored on the held-out test half (primary result) and on the
     full 246-pair pool (secondary), with real and synthetic CVs also reported
     separately.

Usage:  .venv/bin/python -m experiments.run_revision
Writes: experiments/results/revision_results.json
"""
import hashlib
import json
import os
import random
import sqlite3
import time
from dataclasses import asdict, replace

import numpy as np
from scipy.stats import wilcoxon

from app.database import SessionLocal
from app.models import CV, JobDescription, ReviewerLabel
from app.services.metrics import metrics
from app.services.ranking import ORIGINAL_CONFIG, REVISED_CONFIG, rank

EVAL_JD_IDS = [51, 52, 53, 54, 55]
SPLIT_SEED = 20261014
BOOTSTRAP_SEED = 7
BOOTSTRAP_B = 10_000
THRESHOLD_GRID = [(0.20, 0.40), (0.30, 0.50), (0.40, 0.60), (0.50, 0.70), (0.60, 0.80), (0.70, 0.90)]
METRIC_KEYS = ["ndcg@5", "ndcg@10", "map", "mrr", "recall@10", "recall@20"]
HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(HERE), "raematch.db")


def snapshot_hash() -> str:
    """Hash of the rows that determine every result (CV text/parse output,
    JD requirements, labels), so the snapshot can be identified later."""
    con = sqlite3.connect(DB_PATH)
    h = hashlib.sha256()
    for sql in (
        "select id, clean_text, sections_json, skills_json, years_experience, seniority from cvs order by id",
        "select id, title, description, requirements_json, minimum_years, required_seniority from job_descriptions order by id",
        "select jd_id, cv_id, label from reviewer_labels order by jd_id, cv_id",
    ):
        for row in con.execute(sql):
            h.update(repr(row).encode())
    con.close()
    return h.hexdigest()


def split_labels(labels_by_jd):
    split = {}
    for jd_id, labels in labels_by_jd.items():
        ids = sorted(labels)
        random.Random(SPLIT_SEED + jd_id).shuffle(ids)
        half = len(ids) // 2
        split[jd_id] = {"dev": set(ids[:half]), "test": set(ids[half:])}
    return split


def score(order, labels, keep=None):
    seq = [labels[c] for c in order if c in labels and (keep is None or c in keep)]
    return metrics(seq) if seq else None


def macro(per_jd):
    vals = [m for m in per_jd.values() if m]
    return {k: round(float(np.mean([m[k] for m in vals])), 4) for k in METRIC_KEYS}


def bootstrap_ci(values, rng):
    values = np.asarray(values)
    draws = rng.integers(0, len(values), size=(BOOTSTRAP_B, len(values)))
    means = values[draws].mean(axis=1)
    return [round(float(np.percentile(means, 2.5)), 4), round(float(np.percentile(means, 97.5)), 4)]


def top10_rates(rows):
    """Constraint-violation and unsupported-claim rate over a top-10 list."""
    violations = sum(1 for r in rows if r["hard_pass"] is False)
    skill = [a for r in rows for a in r["assessments"] if a["category"] == "skill"]
    unsupported = sum(1 for a in skill if a["status"] == "unsupported")
    fail_cats = {}
    for r in rows:
        for a in r["assessments"]:
            if a["kind"] == "hard" and a["status"] != "satisfied":
                fail_cats[a["category"]] = fail_cats.get(a["category"], 0) + 1
    return {
        "violation_rate@10": round(violations / len(rows), 4) if rows else None,
        "unsupported_claim_rate@10": round(unsupported / len(skill), 4) if skill else 0.0,
        "hard_fail_categories": fail_cats,
    }


def main():
    db = SessionLocal()
    cvs = db.query(CV).order_by(CV.id).all()
    source = {cv.id: cv.source_type for cv in cvs}
    jds = {jd_id: db.get(JobDescription, jd_id) for jd_id in EVAL_JD_IDS}
    labels = {
        jd_id: {r.cv_id: r.label for r in db.query(ReviewerLabel).filter_by(jd_id=jd_id)}
        for jd_id in EVAL_JD_IDS
    }
    split = split_labels(labels)
    out = {
        "snapshot": {
            "db": "raematch.db",
            "sha256": snapshot_hash(),
            "corpus_size": len(cvs),
            "real": sum(1 for s in source.values() if s == "real"),
            "synthetic": sum(1 for s in source.values() if s == "synthetic"),
            "labeled_pairs": sum(len(v) for v in labels.values()),
        },
        "split": {
            "seed": SPLIT_SEED,
            "per_jd": {j: {"dev": len(s["dev"]), "test": len(s["test"])} for j, s in split.items()},
        },
    }
    print(json.dumps(out, indent=1), flush=True)

    # 1. Calibrate the revised model's thresholds on the development half.
    calibration = []
    for low, high in THRESHOLD_GRID:
        cfg = replace(REVISED_CONFIG, low=low, high=high)
        dev, test, full = {}, {}, {}
        for jd_id, jd in jds.items():
            order = [r["cv_id"] for r in rank(jd, cvs, len(cvs), "full", cfg)]
            dev[jd_id] = score(order, labels[jd_id], split[jd_id]["dev"])
            test[jd_id] = score(order, labels[jd_id], split[jd_id]["test"])
            full[jd_id] = score(order, labels[jd_id])
        row = {
            "low": low,
            "high": high,
            "dev_ndcg@10": macro(dev)["ndcg@10"],
            "test_ndcg@10": macro(test)["ndcg@10"],
            "full_ndcg@10": macro(full)["ndcg@10"],
        }
        calibration.append(row)
        print("calibration", row, flush=True)
    best = max(calibration, key=lambda r: r["dev_ndcg@10"])
    final_cfg = replace(REVISED_CONFIG, low=best["low"], high=best["high"])
    out["calibration"] = {"grid": calibration, "selected": [best["low"], best["high"]]}
    out["final_config"] = asdict(final_cfg)
    out["original_config"] = asdict(ORIGINAL_CONFIG)

    # 2. Score every model under the frozen configuration.
    models = {
        "M1": ("TF-IDF", "tfidf", final_cfg),
        "M2": ("SBERT full text (MiniLM)", "sbert_full", final_cfg),
        "M3": ("Section-level SBERT", "section_sbert", final_cfg),
        "M4": ("Requirement-aware", "requirement_aware", final_cfg),
        "M5": ("Requirement + seniority", "requirement_seniority", final_cfg),
        "M6": ("Full proposed model (revised)", "full", final_cfg),
        "M6-orig": ("Full proposed model (original config)", "full", ORIGINAL_CONFIG),
    }
    results = {}
    for mid, (name, method, cfg) in models.items():
        res = {"name": name, "test": {}, "full": {}, "real": {}, "synthetic": {}, "seconds": {}, "top10": {}}
        for jd_id, jd in jds.items():
            t0 = time.time()
            ranked = rank(jd, cvs, len(cvs), method, cfg)
            res["seconds"][jd_id] = round(time.time() - t0, 2)
            order = [r["cv_id"] for r in ranked]
            rows = ranked[:10]
            lab = labels[jd_id]
            res["test"][jd_id] = score(order, lab, split[jd_id]["test"])
            res["full"][jd_id] = score(order, lab)
            res["real"][jd_id] = score(order, lab, {c for c in lab if source[c] == "real"})
            res["synthetic"][jd_id] = score(order, lab, {c for c in lab if source[c] == "synthetic"})
            if rows and rows[0].get("hard_pass") is not None:
                res["top10"][jd_id] = top10_rates(rows)
        for part in ("test", "full", "real", "synthetic"):
            res[part + "_macro"] = macro(res[part])
        results[mid] = res
        print(mid, name, "test", res["test_macro"], "full", res["full_macro"], flush=True)
    out["models"] = results

    # 3. Uncertainty: bootstrap over JDs and paired comparison with M6.
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    stats = {}
    for part in ("test", "full"):
        stats[part] = {}
        m6 = {k: [results["M6"][part][j][k] for j in EVAL_JD_IDS] for k in ("ndcg@10", "map")}
        for mid, res in results.items():
            entry = {}
            for k in ("ndcg@10", "map"):
                vals = [res[part][j][k] for j in EVAL_JD_IDS]
                entry[k + "_ci"] = bootstrap_ci(vals, rng)
                if mid != "M6":
                    diff = np.asarray(vals) - np.asarray(m6[k])
                    entry[k + "_diff_vs_M6"] = round(float(diff.mean()), 4)
                    entry[k + "_diff_ci"] = bootstrap_ci(diff, rng)
                    entry[k + "_wilcoxon_p"] = (
                        round(float(wilcoxon(diff).pvalue), 4) if np.any(diff != 0) else 1.0
                    )
            stats[part][mid] = entry
    out["statistics"] = stats

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    path = os.path.join(HERE, "results", "revision_results.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print("saved", path)


if __name__ == "__main__":
    main()
