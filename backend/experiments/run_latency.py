"""Per-JD ranking latency of M1-M6 under the revised configuration, on the
same frozen snapshot, after one warm-up pass (embedding cache built).

Usage:  .venv/bin/python -m experiments.run_latency
Writes: experiments/results/latency_results.json
"""
import json
import os
import time

from app.database import SessionLocal
from app.models import CV, JobDescription
from app.services.ranking import METHODS, REVISED_CONFIG, rank, warm_cv_embedding_cache

EVAL_JD_IDS = [51, 52, 53, 54, 55]
REPEATS = 2
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    db = SessionLocal()
    cvs = db.query(CV).order_by(CV.id).all()
    jds = [db.get(JobDescription, j) for j in EVAL_JD_IDS]

    t0 = time.time()
    warm_cv_embedding_cache(cvs)
    index_build = time.time() - t0
    for method in METHODS:  # warm-up pass, not timed
        rank(jds[0], cvs, len(cvs), method, REVISED_CONFIG)

    out = {"corpus_size": len(cvs), "index_build_seconds": round(index_build, 1), "per_method": {}}
    for method in METHODS:
        times = []
        for jd in jds:
            for _ in range(REPEATS):
                t = time.time()
                rank(jd, cvs, len(cvs), method, REVISED_CONFIG)
                times.append(time.time() - t)
        out["per_method"][method] = {
            "mean_seconds": round(sum(times) / len(times), 2),
            "min_seconds": round(min(times), 2),
            "max_seconds": round(max(times), 2),
        }
        print(method, out["per_method"][method], flush=True)

    with open(os.path.join(HERE, "results", "latency_results.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
