"""Re-run of the controlled robustness battery (3 instances per category) under
the original and the revised configuration, on the same frozen snapshot as
run_revision.py. Reads the calibrated configuration from
experiments/results/revision_results.json.

Usage:  .venv/bin/python -m experiments.run_battery
Writes: experiments/results/battery_results.json
"""
import json
import os

from app.database import SessionLocal
from app.models import CV, JobDescription
from app.services.ranking import METHODS, ORIGINAL_CONFIG, RankConfig, rank

HERE = os.path.dirname(os.path.abspath(__file__))

# category -> list of (jd_id, {role: candidate_id})
BATTERY = {
    "seniority": [
        (56, {"fresher": "ROBUST_SEN_FRESHER", "senior": "ROBUST_SEN_SENIOR"}),
        (59, {"fresher": "ROBUST_SEN2_FRESHER", "senior": "ROBUST_SEN2_SENIOR"}),
        (60, {"fresher": "ROBUST_SEN3_FRESHER", "senior": "ROBUST_SEN3_SENIOR"}),
    ],
    "missing_mandatory": [
        (57, {"has_all": "ROBUST_MISSING_HAS_ALL", "missing": "ROBUST_MISSING_NO_DB"}),
        (61, {"has_all": "ROBUST_MISS2_HAS_ALL", "missing": "ROBUST_MISS2_NO_TERRAFORM"}),
        (62, {"has_all": "ROBUST_MISS3_HAS_ALL", "missing": "ROBUST_MISS3_NO_CYPRESS"}),
    ],
    "role_confusion": [
        (58, {"genuine": "ROBUST_ROLE_GENUINE_DEV", "confused": "ROBUST_ROLE_CONFUSED_PM"}),
        (63, {"genuine": "ROBUST_ROLE2_GENUINE_DEV", "confused": "ROBUST_ROLE2_CONFUSED_BA"}),
        (64, {"genuine": "ROBUST_ROLE3_GENUINE_DEV", "confused": "ROBUST_ROLE3_CONFUSED_QA"}),
    ],
    "keyword_stuffing": [
        (51, {"original": "ROBUST_STUFF_ORIGINAL", "stuffed": "ROBUST_STUFF_STUFFED", "supported": "ROBUST_STUFF_SUPPORTED"}),
        (65, {"original": "ROBUST_STUFF2_ORIGINAL", "stuffed": "ROBUST_STUFF2_STUFFED", "supported": "ROBUST_STUFF2_SUPPORTED"}),
        (66, {"original": "ROBUST_STUFF3_ORIGINAL", "stuffed": "ROBUST_STUFF3_STUFFED", "supported": "ROBUST_STUFF3_SUPPORTED"}),
    ],
}

# Expected H_pass for each role (None = not a gating test).
EXPECTED_PASS = {
    "fresher": False, "senior": True,
    "has_all": True, "missing": False,
    "genuine": True, "confused": False,
}


def main():
    with open(os.path.join(HERE, "results", "revision_results.json")) as f:
        final_cfg = RankConfig(**json.load(f)["final_config"])
    configs = {"original": ORIGINAL_CONFIG, "revised": final_cfg}

    db = SessionLocal()
    cvs = db.query(CV).order_by(CV.id).all()
    by_candidate = {cv.candidate_id: cv.id for cv in cvs}
    out = {"corpus_size": len(cvs), "configs": {k: vars(v) for k, v in configs.items()}, "cases": []}

    for category, instances in BATTERY.items():
        for jd_id, roles in instances:
            jd = db.get(JobDescription, jd_id)
            case = {"category": category, "jd_id": jd_id, "jd": jd.title, "ranks": {}, "gate": {}}
            for cfg_name, cfg in configs.items():
                case["ranks"][cfg_name] = {}
                for method in METHODS:
                    ranked = rank(jd, cvs, len(cvs), method, cfg)
                    pos = {r["cv_id"]: r for r in ranked}
                    case["ranks"][cfg_name][method] = {
                        role: pos[by_candidate[cid]]["rank"] for role, cid in roles.items()
                    }
                    if method in ("requirement_seniority", "full"):
                        case["gate"].setdefault(cfg_name, {})[method] = {
                            role: {
                                "hard_pass": pos[by_candidate[cid]]["hard_pass"],
                                "hard": [
                                    (a["requirement"], a["status"], a["score"])
                                    for a in pos[by_candidate[cid]]["assessments"]
                                    if a["kind"] == "hard"
                                ],
                            }
                            for role, cid in roles.items()
                        }
            out["cases"].append(case)
            print(category, jd_id, json.dumps(case["ranks"]["revised"]["full"]),
                  {r: case["gate"]["revised"]["full"][r]["hard_pass"] for r in roles}, flush=True)

    # Summary rates for M6 under each configuration.
    summary = {}
    for cfg_name in configs:
        rows = {}
        for case in out["cases"]:
            gate = case["gate"][cfg_name]["full"]
            for role, info in gate.items():
                if role in EXPECTED_PASS:
                    key = f"{case['category']}:{role}"
                    rows.setdefault(key, [0, 0])
                    rows[key][0] += int(info["hard_pass"] == EXPECTED_PASS[role])
                    rows[key][1] += 1
            if case["category"] == "keyword_stuffing":
                r = case["ranks"][cfg_name]["full"]
                rows.setdefault("keyword_stuffing:monotonic", [0, 0])
                rows["keyword_stuffing:monotonic"][0] += int(r["original"] > r["stuffed"] > r["supported"])
                rows["keyword_stuffing:monotonic"][1] += 1
                rows.setdefault("keyword_stuffing:no_gain_from_stuffing", [0, 0])
                rows["keyword_stuffing:no_gain_from_stuffing"][0] += int(r["stuffed"] >= r["original"])
                rows["keyword_stuffing:no_gain_from_stuffing"][1] += 1
                rows.setdefault("keyword_stuffing:gate_only_supported", [0, 0])
                g = gate
                rows["keyword_stuffing:gate_only_supported"][0] += int(
                    g["supported"]["hard_pass"] and not g["stuffed"]["hard_pass"]
                )
                rows["keyword_stuffing:gate_only_supported"][1] += 1
        summary[cfg_name] = {k: f"{a}/{b}" for k, (a, b) in rows.items()}
    out["summary_M6"] = summary
    print(json.dumps(summary, indent=1))

    with open(os.path.join(HERE, "results", "battery_results.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
