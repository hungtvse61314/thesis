import os
import sys
import json

os.environ["DATABASE_URL"] = "sqlite:///raematch_experiment_A3.db"
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models import CV, JobDescription
from app.services.ranking import rank

EVAL_JD_IDS = [51, 52, 53, 54, 55]

db = SessionLocal()
cvs = db.query(CV).filter(~CV.candidate_id.like("ROBUST_%")).all()

out = {}
for jd_id in EVAL_JD_IDS:
    jd = db.get(JobDescription, jd_id)
    ranked = rank(jd, cvs, 10, method="full")
    total_skill_reqs = 0
    unsupported = 0
    hard_fail_categories = {}
    for row in ranked:
        for a in row["assessments"]:
            if a["category"] == "skill":
                total_skill_reqs += 1
                if a["status"] == "unsupported":
                    unsupported += 1
            if a["kind"] == "hard" and a["status"] != "satisfied":
                hard_fail_categories[a["category"]] = hard_fail_categories.get(a["category"], 0) + 1
    rate = unsupported / total_skill_reqs if total_skill_reqs else 0.0
    out[jd_id] = {
        "unsupported_claim_rate_at_10": round(rate, 4),
        "hard_fail_categories_top10": hard_fail_categories,
    }
    print(jd_id, jd.title, out[jd_id], flush=True)

with open("a3_unsupported_rates.json", "w") as f:
    json.dump(out, f, indent=2)
