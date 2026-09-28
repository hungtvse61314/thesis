import os
import sys
import json
import time

os.environ["DATABASE_URL"] = "sqlite:///raematch_experiment_A3.db"
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models import CV, JobDescription, ReviewerLabel
from app.services.ranking import rank, METHODS
from app.services.metrics import metrics

EVAL_JD_IDS = [51, 52, 53, 54, 55]

db = SessionLocal()

cvs = db.query(CV).filter(~CV.candidate_id.like("ROBUST_%")).all()
print(f"corpus size (excluding robustness-battery CVs): {len(cvs)}", flush=True)

per_jd_results = {}  # jd_id -> method_id -> metrics dict
per_jd_hardpass_top10 = {}  # jd_id -> method_id -> list of hard_pass bools for top 10

t0 = time.time()
for jd_id in EVAL_JD_IDS:
    jd = db.get(JobDescription, jd_id)
    labels = {r.cv_id: r.label for r in db.query(ReviewerLabel).filter_by(jd_id=jd_id).all()}
    print(f"\n=== JD {jd_id} ({jd.title}) : {len(labels)} labeled pairs ===", flush=True)
    per_jd_results[jd_id] = {}
    per_jd_hardpass_top10[jd_id] = {}
    for method_id in METHODS:
        t1 = time.time()
        ranked = rank(jd, cvs, len(cvs), method=method_id)
        sequence = [labels[r["cv_id"]] for r in ranked if r["cv_id"] in labels]
        m = metrics(sequence) if sequence else None
        per_jd_results[jd_id][method_id] = m
        top10 = ranked[:10]
        # violation: hard_pass is False/None-for-no-gate; for M4 hard_pass is None (no gate)
        per_jd_hardpass_top10[jd_id][method_id] = [row["hard_pass"] for row in top10]
        dt = time.time() - t1
        print(f"  {method_id:22s} {m} ({dt:.1f}s)", flush=True)

print(f"\nTotal time: {time.time()-t0:.1f}s", flush=True)

with open("a3_results.json", "w") as f:
    json.dump(
        {
            "per_jd_results": per_jd_results,
            "per_jd_hardpass_top10": per_jd_hardpass_top10,
            "corpus_size": len(cvs),
        },
        f,
        indent=2,
    )
print("saved a3_results.json")
