from dataclasses import dataclass
from functools import lru_cache
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .text_processing import extract_skills, split_sentences, loads
from .experience import level_score


@dataclass(frozen=True)
class RankConfig:
    """Every tunable of the M4-M6 assessment, so one experiment run is pinned
    to exactly one configuration (thesis Section 4.x "Revised configuration")."""

    low: float = 0.35
    high: float = 0.55
    # None keeps the parsed kind; "soft" demotes every JD responsibility
    # sentence, which otherwise gates H_pass at a threshold meant for skills.
    responsibility_kind: str | None = None
    # "full_text": a skill counts as declared if it appears anywhere in the CV.
    # "skills_section": only if it appears in the CV's Skills section.
    declared_scope: str = "full_text"
    # Reject exact-term evidence that only describes a project ("a Java-based
    # platform") rather than the candidate's own use of the skill.
    descriptor_filter: bool = False
    # Ordinal value of "unsupported"; 0 removes the reward for declaring a
    # skill without evidence (keyword stuffing).
    unsupported_value: int = 1

    def status_value(self, status: str) -> int:
        if status == "unsupported":
            return self.unsupported_value
        return STATUS_VALUE[status]


STATUS_VALUE = {
    "not_satisfied": 0,
    "unsupported": 1,
    "partially_satisfied": 2,
    "satisfied": 3,
}

# Configuration used for the original thesis submission (kept for comparison).
ORIGINAL_CONFIG = RankConfig()
# Revised configuration; thresholds were selected on the development half of
# the labeled pool (experiments/run_revision.py, grid (0.20,0.40)..(0.70,0.90)).
REVISED_CONFIG = RankConfig(
    low=0.70,
    high=0.90,
    responsibility_kind="soft",
    declared_scope="skills_section",
    descriptor_filter=True,
    unsupported_value=0,
)
DEFAULT_CONFIG = REVISED_CONFIG

LOW_THRESHOLD = DEFAULT_CONFIG.low
HIGH_THRESHOLD = DEFAULT_CONFIG.high

DESCRIPTOR_SUFFIX_RE = re.compile(
    r"\s*-?\s*(?:based|powered|driven|centric|oriented|enabled|backed)\b"
)

# Experimental model catalogue (thesis Table "Experimental model comparison",
# M1-M6). Exposed so the API and frontend can list valid `method` values with
# a human-readable label instead of hardcoding the mapping in two places.
METHODS = {
    "tfidf": "M1 - TF-IDF full text",
    "sbert_full": "M2 - SBERT full text",
    "section_sbert": "M3 - Section-level SBERT",
    "requirement_aware": "M4 - Requirement-aware (no evidence verification)",
    "requirement_seniority": "M5 - Requirement + seniority constraints",
    "full": "M6 - Full proposed model",
}

# Per-CV sentence embeddings, keyed by CV id and guarded by a content hash so a
# reused id with different text (or an in-place edit) can never serve a stale
# entry. Ranking re-embeds the JD/requirements on every call (cheap, a handful
# of short strings) but CV text is the expensive, repeated part: without this
# cache, ranking against N JDs re-embeds every CV's evidence sentences N times.
_CV_EMBEDDING_CACHE: dict[int, tuple[int, dict]] = {}

SECTION_FACETS = ("skills", "experience", "education")


def invalidate_cv_embedding_cache(cv_id: int) -> None:
    _CV_EMBEDDING_CACHE.pop(cv_id, None)


@lru_cache(maxsize=1)
def sentence_model():
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def _encode(texts: list[str]):
    """Batch-embed texts with the sentence model. None if the model is unavailable."""
    if not texts:
        return np.zeros((0, 0))
    model = sentence_model()
    if model is None:
        return None
    try:
        return np.asarray(
            model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        )
    except Exception:
        return None


def _tfidf_similarities(query: str, docs: list[str]) -> list[float]:
    """Deterministic lexical similarity, used both as the SBERT fallback and
    as the explicit M1 (TF-IDF) baseline."""
    if not docs:
        return []
    vect = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    try:
        mat = vect.fit_transform([query] + docs)
    except ValueError:
        return [0.0] * len(docs)
    return cosine_similarity(mat[0], mat[1:])[0].clip(0, 1).tolist()


def similarities(query: str, docs: list[str]) -> list[float]:
    if not docs:
        return []
    arr = _encode([query] + docs)
    if arr is not None:
        return np.dot(arr[1:], arr[0]).clip(0, 1).tolist()
    return _tfidf_similarities(query, docs)


def contains_exact_term(text: str, term: str) -> bool:
    if not text or not term:
        return False
    pattern = rf"(?<!\w){re.escape(term.lower())}(?!\w)"
    return re.search(pattern, text.lower()) is not None


def contains_skill_use(text: str, term: str) -> bool:
    """Like contains_exact_term, but ignores mentions that only qualify a
    product ("Java-based platform", "Docker-based pipeline")."""
    if not text or not term:
        return False
    low = text.lower()
    pattern = rf"(?<!\w){re.escape(term.lower())}(?!\w)"
    return any(
        not DESCRIPTOR_SUFFIX_RE.match(low, m.end()) for m in re.finditer(pattern, low)
    )


# Skills-section skills per CV, keyed by CV id and guarded by a hash of the
# parsed sections; computed once per CV instead of once per (CV, requirement).
_SKILLS_SECTION_CACHE: dict[int, tuple[int, frozenset[str]]] = {}


def declared_skills(cv, config: RankConfig) -> frozenset[str] | set[str]:
    if config.declared_scope == "skills_section":
        key = hash(cv.sections_json or "")
        cached = _SKILLS_SECTION_CACHE.get(cv.id)
        if cached is not None and cached[0] == key:
            return cached[1]
        sections = loads(cv.sections_json, {})
        skills = frozenset(extract_skills(sections.get("skills", "")))
        _SKILLS_SECTION_CACHE[cv.id] = (key, skills)
        return skills
    return {
        x.strip().lower()
        for x in loads(cv.skills_json, [])
        if isinstance(x, str) and x.strip()
    }


def _cv_text_block(cv) -> tuple[list[str], list[str], list[str]]:
    """Evidence sentences, section texts, and the full ordered text list to
    embed for one CV: [clean_text, skills, experience, education, *evidence]."""
    sections = loads(cv.sections_json, {})
    evidence_text = (
        sections.get("experience", "") + "\n" + sections.get("projects", "")
    ).strip()
    evidence_sentences = split_sentences(evidence_text)[:200]
    section_texts = [sections.get(facet, "") for facet in SECTION_FACETS]
    texts = [cv.clean_text or ""] + section_texts + evidence_sentences
    return evidence_sentences, section_texts, texts


def _pack_cv_entry(embeddings, evidence_sentences: list[str], section_texts: list[str]) -> dict:
    if embeddings is not None:
        baseline_embedding = embeddings[0]
        section_embeddings = dict(zip(SECTION_FACETS, embeddings[1 : 1 + len(SECTION_FACETS)]))
        evidence_embeddings = embeddings[1 + len(SECTION_FACETS) :]
    else:
        baseline_embedding = None
        section_embeddings = {facet: None for facet in SECTION_FACETS}
        evidence_embeddings = None
    return {
        "evidence_sentences": evidence_sentences,
        "section_texts": dict(zip(SECTION_FACETS, section_texts)),
        "baseline_embedding": baseline_embedding,
        "section_embeddings": section_embeddings,
        "evidence_embeddings": evidence_embeddings,
    }


def _cv_embeddings(cv) -> dict:
    """Evidence-pool, baseline, and section embeddings for a CV, cached across
    ranking calls (see module docstring above for the invalidation strategy)."""
    content_hash = hash(cv.clean_text or "")
    cached = _CV_EMBEDDING_CACHE.get(cv.id)
    if cached is not None and cached[0] == content_hash:
        return cached[1]

    evidence_sentences, section_texts, texts_to_embed = _cv_text_block(cv)
    embeddings = _encode(texts_to_embed)
    entry = _pack_cv_entry(embeddings, evidence_sentences, section_texts)
    _CV_EMBEDDING_CACHE[cv.id] = (content_hash, entry)
    return entry


def warm_cv_embedding_cache(cvs: list) -> int:
    """Embed every not-yet-cached CV in a single batched call instead of one
    `_encode()` call per CV. Per-call overhead (tokenization, Python/C++
    round-trip) dominates when a corpus has thousands of CVs, so submitting
    one flat batch of all their texts together is dramatically faster than
    looping `_cv_embeddings()` one CV at a time. Returns how many CVs were
    (re-)embedded."""
    pending = []
    for cv in cvs:
        content_hash = hash(cv.clean_text or "")
        cached = _CV_EMBEDDING_CACHE.get(cv.id)
        if cached is None or cached[0] != content_hash:
            pending.append((cv, content_hash))
    if not pending:
        return 0

    flat_texts: list[str] = []
    spans: list[tuple[int, int]] = []
    blocks = []
    for cv, content_hash in pending:
        evidence_sentences, section_texts, texts = _cv_text_block(cv)
        start = len(flat_texts)
        flat_texts.extend(texts)
        spans.append((start, len(flat_texts)))
        blocks.append((cv, content_hash, evidence_sentences, section_texts))

    embeddings = _encode(flat_texts)
    for (cv, content_hash, evidence_sentences, section_texts), (start, end) in zip(blocks, spans):
        chunk = embeddings[start:end] if embeddings is not None else None
        entry = _pack_cv_entry(chunk, evidence_sentences, section_texts)
        _CV_EMBEDDING_CACHE[cv.id] = (content_hash, entry)
    return len(pending)


def assess_requirement(req: dict, cv, req_embedding=None, config: RankConfig = DEFAULT_CONFIG) -> dict:
    """Full evidence-aware assessment (M6): semantic evidence retrieval against
    Experience/Projects sentences, with exact-term corroboration."""
    text = req["text"]
    category = req.get("category", "skill")
    kind = req.get("kind", "hard")
    declared = declared_skills(cv, config)
    req_skills = {
        x.strip().lower() for x in extract_skills(text) if isinstance(x, str) and x.strip()
    }

    if category == "experience":
        required = float(req.get("minimum_years") or 0)
        detected = float(cv.years_experience or 0)
        ok = detected >= required
        evidence = (
            f"{detected:.1f} years detected"
            if getattr(cv, "years_detected", True)
            else f"No years-of-experience phrase found in CV text (defaulted to {detected:.1f})"
        )
        return {
            "requirement": text,
            "kind": kind,
            "category": category,
            "status": "satisfied" if ok else "not_satisfied",
            "score": 1.0 if ok else 0.0,
            "evidence_score": 1.0 if ok else 0.0,
            "evidence": evidence,
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

    cache = _cv_embeddings(cv)
    evidence_pool = cache["evidence_sentences"]

    if req_embedding is None:
        embedded_query = _encode([text])
        req_embedding = embedded_query[0] if embedded_query is not None else None

    if req_embedding is not None and cache["evidence_embeddings"] is not None:
        if evidence_pool:
            sims = cache["evidence_embeddings"] @ req_embedding
            best_index = int(np.argmax(sims))
            best_score = float(np.clip(sims[best_index], 0, 1))
            best_sentence = evidence_pool[best_index]
        else:
            best_score = 0.0
            best_sentence = ""
    else:
        # Sentence-transformers unavailable anywhere in this call: fall back to
        # the uncached, per-call TF-IDF path (offline/demo environments only).
        scores = similarities(text, evidence_pool) if evidence_pool else []
        if scores:
            best_index = int(np.argmax(scores))
            best_score = float(scores[best_index])
            best_sentence = evidence_pool[best_index]
        else:
            best_score = 0.0
            best_sentence = ""

    exact_declared = bool(req_skills and any(s in declared for s in req_skills))
    term_match = contains_skill_use if config.descriptor_filter else contains_exact_term
    exact_evidence = bool(
        req_skills
        and best_sentence
        and any(term_match(best_sentence, s) for s in req_skills)
    )

    valid_evidence = None
    if exact_evidence or best_score >= config.high:
        status = "satisfied"
        valid_evidence = best_sentence
    elif best_score >= config.low:
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


def assess_requirement_declared_only(req: dict, cv, req_embedding=None, config: RankConfig = DEFAULT_CONFIG) -> dict:
    """Shallow assessment used by M4/M5: checks whether a requirement is
    *declared* in the CV's Skills list, without retrieving or verifying any
    Experience/Project evidence sentence. `req_embedding` is accepted (and
    ignored) purely so this function is interchangeable with
    `assess_requirement` in the shared ranking loop."""
    text = req["text"]
    category = req.get("category", "skill")
    kind = req.get("kind", "hard")

    if category == "experience":
        required = float(req.get("minimum_years") or 0)
        detected = float(cv.years_experience or 0)
        ok = detected >= required
        evidence = (
            f"{detected:.1f} years detected"
            if getattr(cv, "years_detected", True)
            else f"No years-of-experience phrase found in CV text (defaulted to {detected:.1f})"
        )
        return {
            "requirement": text,
            "kind": kind,
            "category": category,
            "status": "satisfied" if ok else "not_satisfied",
            "score": 1.0 if ok else 0.0,
            "evidence_score": 1.0 if ok else 0.0,
            "evidence": evidence,
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

    declared = declared_skills(cv, config)
    req_skills = {
        x.strip().lower() for x in extract_skills(text) if isinstance(x, str) and x.strip()
    } or {text.strip().lower()}

    is_declared = any(s in declared for s in req_skills) or contains_exact_term(
        cv.clean_text or "", text
    )
    status = "satisfied" if is_declared else "not_satisfied"
    return {
        "requirement": text,
        "kind": kind,
        "category": category,
        "status": status,
        "score": 1.0 if is_declared else 0.0,
        "evidence_score": 1.0 if is_declared else 0.0,
        "evidence": "Declared in Skills" if is_declared else None,
    }


def _requirements_for_jd(jd, config: RankConfig = DEFAULT_CONFIG) -> list[dict]:
    requirements = [
        {**r, "kind": config.responsibility_kind}
        if config.responsibility_kind and r.get("category") == "responsibility"
        else r
        for r in loads(jd.requirements_json, [])
    ]
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
    return requirements


def _base_row(cv) -> dict:
    return {
        "cv_id": cv.id,
        "candidate_id": cv.candidate_id,
        "role_title": cv.role_title,
        "source_type": cv.source_type,
        "years_experience": cv.years_experience,
        "seniority": cv.seniority,
        "parse_status": cv.parse_status,
        "file_name": cv.file_name,
        "pdf_url": f"/api/cvs/{cv.id}/pdf" if cv.file_path else None,
    }


def _baseline_scores(jd_query: str, cvs: list) -> list[float]:
    """Full-document SBERT similarity (cached per CV), used as M2 and as the
    lexicographic tie-breaker for M5/M6."""
    cv_caches = [_cv_embeddings(cv) for cv in cvs]
    jd_embedding = _encode([jd_query])
    if jd_embedding is not None and all(c["baseline_embedding"] is not None for c in cv_caches):
        baseline_matrix = np.stack([c["baseline_embedding"] for c in cv_caches])
        return (baseline_matrix @ jd_embedding[0]).clip(0, 1).tolist()
    return similarities(jd_query, [cv.clean_text for cv in cvs])


def _finalize(rows: list[dict], top_k: int) -> list[dict]:
    rows.sort(key=lambda x: x["_sort_key"], reverse=True)
    for index, row in enumerate(rows, 1):
        row["rank"] = index
        row.pop("_sort_key", None)
    return rows[:top_k]


def _rank_tfidf(jd, cvs: list, top_k: int) -> list[dict]:
    scores = _tfidf_similarities(jd.title + " " + jd.description, [cv.clean_text for cv in cvs])
    rows = []
    for cv, score in zip(cvs, scores):
        row = _base_row(cv)
        row.update(
            baseline_score=round(float(score), 4),
            ranking_key=[round(float(score), 4)],
            hard_pass=None,
            assessments=[],
            _sort_key=(float(score),),
        )
        rows.append(row)
    return _finalize(rows, top_k)


def _rank_sbert_full(jd, cvs: list, top_k: int) -> list[dict]:
    scores = _baseline_scores(jd.title + " " + jd.description, cvs)
    rows = []
    for cv, score in zip(cvs, scores):
        row = _base_row(cv)
        row.update(
            baseline_score=round(float(score), 4),
            ranking_key=[round(float(score), 4)],
            hard_pass=None,
            assessments=[],
            _sort_key=(float(score),),
        )
        rows.append(row)
    return _finalize(rows, top_k)


def _rank_section_sbert(jd, cvs: list, top_k: int) -> list[dict]:
    jd_query = jd.title + " " + jd.description
    jd_embedding = _encode([jd_query])
    cv_caches = [_cv_embeddings(cv) for cv in cvs]

    rows = []
    for cv, cache in zip(cvs, cv_caches):
        facet_scores = []
        if jd_embedding is not None and cache["baseline_embedding"] is not None:
            facet_scores.append(float(np.clip(cache["baseline_embedding"] @ jd_embedding[0], 0, 1)))
            for facet in SECTION_FACETS:
                text = cache["section_texts"].get(facet, "")
                facet_embedding = cache["section_embeddings"].get(facet)
                if text.strip() and facet_embedding is not None:
                    facet_scores.append(float(np.clip(facet_embedding @ jd_embedding[0], 0, 1)))
            score = sum(facet_scores) / len(facet_scores) if facet_scores else 0.0
        else:
            score = similarities(jd_query, [cv.clean_text])[0]

        row = _base_row(cv)
        row.update(
            baseline_score=round(float(score), 4),
            ranking_key=[round(float(score), 4)],
            hard_pass=None,
            assessments=[],
            _sort_key=(float(score),),
        )
        rows.append(row)
    return _finalize(rows, top_k)


def _rank_requirement_aware(jd, cvs: list, top_k: int, requirements: list[dict], config: RankConfig) -> list[dict]:
    """M4: requirement coverage using declared-only assessment, no hard-constraint
    gating and no lexicographic key - candidates are ordered purely by how many
    requirements they declare, tie-broken by full-document similarity."""
    baseline = _baseline_scores(jd.title + " " + jd.description, cvs)
    rows = []
    for cv, b in zip(cvs, baseline):
        assessments = [assess_requirement_declared_only(r, cv, config=config) for r in requirements]
        coverage = (
            sum(config.status_value(a["status"]) / 3 for a in assessments) / len(assessments)
            if assessments
            else 0.0
        )
        row = _base_row(cv)
        row.update(
            baseline_score=round(float(b), 4),
            ranking_key=[round(coverage, 4), round(float(b), 4)],
            hard_pass=None,
            assessments=assessments,
            _sort_key=(coverage, float(b)),
        )
        rows.append(row)
    return _finalize(rows, top_k)


def _rank_lexicographic(jd, cvs: list, top_k: int, requirements: list[dict], assess, config: RankConfig, req_embedding_map=None) -> list[dict]:
    """Shared M5/M6 loop: lexicographic key (Hpass, Ch, Eh, Salign, Cs, Es, B)."""
    baseline = _baseline_scores(jd.title + " " + jd.description, cvs)
    rows = []
    for cv, b in zip(cvs, baseline):
        if req_embedding_map is not None:
            assessments = [assess(r, cv, req_embedding_map.get(r["text"]), config) for r in requirements]
        else:
            assessments = [assess(r, cv, None, config) for r in requirements]
        hard = [a for a in assessments if a["kind"] == "hard"]
        soft = [a for a in assessments if a["kind"] == "soft"]

        def sat(a):
            return config.status_value(a["status"]) / 3

        def coverage(items):
            return sum(sat(x) for x in items) / len(items) if items else 1.0

        def evidence(items):
            return (
                sum(1 for x in items if x["status"] in ("satisfied", "partially_satisfied"))
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
        row = _base_row(cv)
        row.update(
            baseline_score=round(float(b), 4),
            ranking_key=[round(float(x), 4) for x in key],
            hard_pass=bool(hard_pass),
            assessments=assessments,
            _sort_key=key,
        )
        rows.append(row)
    return _finalize(rows, top_k)


def rank(jd, cvs, top_k=10, method="full", config: RankConfig = DEFAULT_CONFIG):
    if method not in METHODS:
        method = "full"

    if method == "tfidf":
        return _rank_tfidf(jd, cvs, top_k)

    # Every other method needs per-CV SBERT embeddings; warm the cache with one
    # batched call up front instead of paying per-CV call overhead 1x per CV
    # inside each of the ranking helpers below.
    warm_cv_embedding_cache(cvs)

    if method == "sbert_full":
        return _rank_sbert_full(jd, cvs, top_k)
    if method == "section_sbert":
        return _rank_section_sbert(jd, cvs, top_k)

    requirements = _requirements_for_jd(jd, config)

    if method == "requirement_aware":
        return _rank_requirement_aware(jd, cvs, top_k, requirements, config)
    if method == "requirement_seniority":
        return _rank_lexicographic(jd, cvs, top_k, requirements, assess_requirement_declared_only, config)

    # method == "full" (M6): batch-embed semantic requirement texts once and
    # reuse each CV's cached embeddings instead of re-encoding per pair.
    semantic_texts = [
        r["text"] for r in requirements if r.get("category") not in ("experience", "seniority")
    ]
    semantic_embeddings = _encode(semantic_texts) if semantic_texts else None
    req_embedding_map = (
        dict(zip(semantic_texts, semantic_embeddings)) if semantic_embeddings is not None else {}
    )
    return _rank_lexicographic(jd, cvs, top_k, requirements, assess_requirement, config, req_embedding_map)
