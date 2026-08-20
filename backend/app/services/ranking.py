from functools import lru_cache
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .text_processing import extract_skills, split_sentences, loads
from .experience import level_score

LOW_THRESHOLD = 0.35
HIGH_THRESHOLD = 0.55
STATUS_VALUE = {
    "not_satisfied": 0,
    "unsupported": 1,
    "partially_satisfied": 2,
    "satisfied": 3,
}


@lru_cache(maxsize=1)
def sentence_model():
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def similarities(query: str, docs: list[str]) -> list[float]:
    if not docs:
        return []
    model = sentence_model()
    if model is not None:
        try:
            arr = model.encode(
                [query] + docs,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return np.dot(arr[1:], arr[0]).clip(0, 1).tolist()
        except Exception:
            pass

    # Deterministic fallback for offline/demo environments.
    vect = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    try:
        mat = vect.fit_transform([query] + docs)
    except ValueError:
        return [0.0] * len(docs)
    return cosine_similarity(mat[0], mat[1:])[0].clip(0, 1).tolist()


def contains_exact_term(text: str, term: str) -> bool:
    if not text or not term:
        return False
    pattern = rf"(?<!\w){re.escape(term.lower())}(?!\w)"
    return re.search(pattern, text.lower()) is not None


def assess_requirement(req: dict, cv) -> dict:
    text = req["text"]
    category = req.get("category", "skill")
    kind = req.get("kind", "hard")
    sections = loads(cv.sections_json, {})
    evidence_text = (
        sections.get("experience", "") + "\n" + sections.get("projects", "")
    ).strip()
    evidence_pool = split_sentences(evidence_text)[:200]
    declared = {
        x.strip().lower()
        for x in loads(cv.skills_json, [])
        if isinstance(x, str) and x.strip()
    }
    req_skills = {
        x.strip().lower() for x in extract_skills(text) if isinstance(x, str) and x.strip()
    }

    if category == "experience":
        required = float(req.get("minimum_years") or 0)
        detected = float(cv.years_experience or 0)
        ok = detected >= required
        return {
            "requirement": text,
            "kind": kind,
            "category": category,
            "status": "satisfied" if ok else "not_satisfied",
            "score": 1.0 if ok else 0.0,
            "evidence_score": 1.0 if ok else 0.0,
            "evidence": f"{detected:.1f} years detected",
        }

    if category == "seniority":
        score = level_score(cv.seniority, req.get("required_seniority") or text)
        status = (
            "satisfied"
            if score >= 1
            else ("partially_satisfied" if score >= 0.5 else "not_satisfied")
        )
        return {
            "requirement": text,
            "kind": kind,
            "category": category,
            "status": status,
            "score": round(float(score), 4),
            "evidence_score": round(float(score), 4),
            "evidence": f"Candidate level: {cv.seniority}",
        }

    scores = similarities(text, evidence_pool) if evidence_pool else []
    if scores:
        best_index = int(np.argmax(scores))
        best_score = float(scores[best_index])
        best_sentence = evidence_pool[best_index]
    else:
        best_score = 0.0
        best_sentence = ""

    exact_declared = bool(req_skills and any(s in declared for s in req_skills))
    exact_evidence = bool(
        req_skills
        and best_sentence
        and any(contains_exact_term(best_sentence, s) for s in req_skills)
    )

    valid_evidence = None
    if exact_evidence or best_score >= HIGH_THRESHOLD:
        status = "satisfied"
        valid_evidence = best_sentence
    elif best_score >= LOW_THRESHOLD:
        status = "partially_satisfied"
        valid_evidence = best_sentence
    elif exact_declared:
        status = "unsupported"
    else:
        status = "not_satisfied"

    return {
        "requirement": text,
        "kind": kind,
        "category": category,
        "status": status,
        "score": round(best_score, 4),
        "evidence_score": round(best_score, 4),
        "evidence": valid_evidence,
    }


def rank(jd, cvs, top_k=10):
    requirements = list(loads(jd.requirements_json, []))
    if jd.minimum_years > 0:
        requirements.append(
            {
                "text": f"Minimum {jd.minimum_years:g} years experience",
                "kind": "hard",
                "category": "experience",
                "minimum_years": jd.minimum_years,
            }
        )
    if jd.required_seniority != "unknown":
        requirements.append(
            {
                "text": jd.required_seniority,
                "kind": "hard",
                "category": "seniority",
                "required_seniority": jd.required_seniority,
            }
        )

    baseline = similarities(
        jd.title + " " + jd.description, [c.clean_text for c in cvs]
    )
    rows = []
    for cv, b in zip(cvs, baseline):
        assessments = [assess_requirement(r, cv) for r in requirements]
        hard = [a for a in assessments if a["kind"] == "hard"]
        soft = [a for a in assessments if a["kind"] == "soft"]

        def sat(a):
            return STATUS_VALUE[a["status"]] / 3

        def coverage(items):
            return sum(sat(x) for x in items) / len(items) if items else 1.0

        def evidence(items):
            return (
                sum(
                    1
                    for x in items
                    if x["status"] in ("satisfied", "partially_satisfied")
                )
                / len(items)
                if items
                else 1.0
            )

        hard_pass = 1 if all(a["status"] == "satisfied" for a in hard) else 0
        years_align = (
            1.0
            if jd.minimum_years <= 0
            else min(float(cv.years_experience or 0) / jd.minimum_years, 1.0)
        )
        seniority_align = level_score(cv.seniority, jd.required_seniority)
        align = (years_align + seniority_align) / 2
        key = (
            hard_pass,
            coverage(hard),
            evidence(hard),
            align,
            coverage(soft),
            evidence(soft),
            float(b),
        )
        rows.append(
            {
                "cv_id": cv.id,
                "candidate_id": cv.candidate_id,
                "role_title": cv.role_title,
                "source_type": cv.source_type,
                "years_experience": cv.years_experience,
                "seniority": cv.seniority,
                "parse_status": cv.parse_status,
                "file_name": cv.file_name,
                "pdf_url": f"/api/cvs/{cv.id}/pdf" if cv.file_path else None,
                "baseline_score": round(float(b), 4),
                "ranking_key": [round(float(x), 4) for x in key],
                "hard_pass": bool(hard_pass),
                "assessments": assessments,
                "key_raw": key,
            }
        )
    rows.sort(key=lambda x: x["key_raw"], reverse=True)
    for index, row in enumerate(rows, 1):
        row["rank"] = index
        row.pop("key_raw", None)
    return rows[:top_k]
