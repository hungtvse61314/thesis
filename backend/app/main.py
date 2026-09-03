import csv
import hashlib
import io
import logging
import os
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .database import Base, engine, get_db, SessionLocal
from .models import CV, JobDescription, ReviewerLabel
from .schemas import JDCreate, LabelCreate
from .services.file_extraction import extract_pdf
from .services.text_processing import (
    clean_text,
    extract_sections,
    extract_skills,
    dumps,
    loads,
)
from .services.experience import extract_years, years_were_detected, infer_seniority
from .services.jd_parsing import parse_jd_requirements
from .services.ranking import (
    rank,
    invalidate_cv_embedding_cache,
    warm_cv_embedding_cache,
    METHODS,
    LOW_THRESHOLD,
    HIGH_THRESHOLD,
)
from .services.metrics import metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("raematch.cv_upload")

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = Path(os.getenv("CV_UPLOAD_DIR", BASE_DIR / "storage" / "cvs"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)


def ensure_sqlite_columns():
    """Small compatibility migration for users upgrading an existing SQLite DB."""
    if not str(engine.url).startswith("sqlite"):
        return
    columns = {c["name"] for c in inspect(engine).get_columns("cvs")}
    if "file_path" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE cvs ADD COLUMN file_path VARCHAR(1000)"))
    if "content_hash" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE cvs ADD COLUMN content_hash VARCHAR(64)"))
    if "years_detected" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE cvs ADD COLUMN years_detected BOOLEAN DEFAULT 1")
            )


ensure_sqlite_columns()

app = FastAPI(
    title="RAEMatch API",
    version="1.2.0",
    description="Requirement-aware and evidence-aware CV-JD ranking system",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _warm_up_embeddings():
    """Pre-embed every indexed CV in a background thread on startup, so the
    multi-minute cold-start cost (see Table 3.9 in the thesis) happens while
    the server boots rather than on the first user-triggered ranking call --
    important before a live demo, where a cold first click can look like the
    app has hung."""
    try:
        db = SessionLocal()
        try:
            cvs = db.query(CV).all()
            if not cvs:
                logger.info("Startup warm-up skipped: no CVs indexed yet")
                return
            logger.info("Startup warm-up: embedding %d CV(s) in the background...", len(cvs))
            started = time.perf_counter()
            n = warm_cv_embedding_cache(cvs)
            logger.info(
                "Startup warm-up finished in %.1fs (%d CV(s) embedded)",
                time.perf_counter() - started, n,
            )
        finally:
            db.close()
    except Exception:
        logger.exception("Startup warm-up failed; ranking will warm the cache lazily instead")


@app.on_event("startup")
def on_startup():
    threading.Thread(target=_warm_up_embeddings, daemon=True).start()


def cv_payload(cv: CV, include_detail: bool = False) -> dict:
    result = {
        "id": cv.id,
        "candidate_id": cv.candidate_id,
        "role_title": cv.role_title,
        "source_type": cv.source_type,
        "skills": loads(cv.skills_json, []),
        "years_experience": cv.years_experience,
        "years_detected": bool(getattr(cv, "years_detected", True)),
        "seniority": cv.seniority,
        "parse_status": cv.parse_status,
        "file_name": cv.file_name,
        "pdf_url": f"/api/cvs/{cv.id}/pdf" if cv.file_path else None,
        "created_at": cv.created_at.isoformat() if cv.created_at else None,
    }
    if include_detail:
        result.update(
            {
                "sections": loads(cv.sections_json, {}),
                "clean_text": cv.clean_text,
            }
        )
    return result


def jd_payload(jd: JobDescription) -> dict:
    return {
        "id": jd.id,
        "title": jd.title,
        "description": jd.description,
        "requirements": loads(jd.requirements_json, []),
        "minimum_years": jd.minimum_years,
        "required_seniority": jd.required_seniority,
        "created_at": jd.created_at.isoformat() if jd.created_at else None,
    }


def save_cv(
    db: Session,
    candidate_id: str,
    text_value: str,
    file_name: str | None = None,
    file_path: str | None = None,
    source_type: str = "real",
    role_title: str = "Candidate",
    parse_status: str = "ok",
):
    normalized = clean_text(text_value)
    if len(normalized) < 100:
        return False, "text_too_short", None
    if db.query(CV).filter(CV.candidate_id == candidate_id).first():
        return False, "duplicate_candidate_id", None

    content_hash = hashlib.sha256(normalized.strip().lower().encode("utf-8")).hexdigest()
    if db.query(CV).filter(CV.content_hash == content_hash).first():
        return False, "duplicate_content", None

    sections = extract_sections(normalized)
    skills = extract_skills(normalized)
    # An explicit (possibly empty) scope, not None: an empty scope means no
    # Summary/Experience/Projects section was recognized, so date ranges
    # elsewhere (Education, Certifications, Awards, Volunteer work) must not
    # be counted as job tenure -- falling back to the full text here would
    # silently reintroduce that bug for exactly the CVs most likely to lack
    # a real work-experience section.
    experience_scope = (
        sections.get("summary", "") + "\n" + sections.get("experience", "") + "\n" + sections.get("projects", "")
    ).strip()
    years = extract_years(normalized, experience_scope)
    detected = years_were_detected(normalized, experience_scope)
    seniority = infer_seniority(normalized, years, experience_scope)
    cv = CV(
        candidate_id=candidate_id,
        file_name=file_name,
        file_path=file_path,
        source_type=source_type,
        role_title=role_title,
        raw_text=normalized,
        clean_text=normalized,
        sections_json=dumps(sections),
        skills_json=dumps(skills),
        years_experience=years,
        years_detected=detected,
        seniority=seniority,
        parse_status=parse_status,
        content_hash=content_hash,
    )
    db.add(cv)
    db.flush()
    return True, None, cv


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "method": "requirement-aware evidence-aware lexicographic reranking",
        "thresholds": {"low": LOW_THRESHOLD, "high": HIGH_THRESHOLD},
    }


@app.post("/api/cvs/upload-pdfs")
async def upload_pdfs(
    files: list[UploadFile] = File(...),
    source_type: str = "real",
    db: Session = Depends(get_db),
):
    batch_started = time.perf_counter()
    logger.info("Upload batch started: %d file(s), source_type=%s", len(files), source_type)

    items = []
    for index, upload in enumerate(files, 1):
        file_started = time.perf_counter()
        original_name = Path(upload.filename or "candidate.pdf").name
        logger.info("[%d/%d] Processing '%s'", index, len(files), original_name)

        if not original_name.lower().endswith(".pdf"):
            logger.warning("[%d/%d] Skipped '%s': not a PDF file", index, len(files), original_name)
            items.append(
                {"file_name": original_name, "status": "skipped", "reason": "pdf_only"}
            )
            continue

        data = await upload.read()
        if not data:
            logger.warning("[%d/%d] Skipped '%s': empty file", index, len(files), original_name)
            items.append(
                {"file_name": original_name, "status": "skipped", "reason": "empty_file"}
            )
            continue
        logger.info("[%d/%d] Read '%s' (%d bytes)", index, len(files), original_name, len(data))

        stored_name = f"{uuid.uuid4().hex}.pdf"
        target = UPLOAD_DIR / stored_name
        target.write_bytes(data)
        logger.info("[%d/%d] Saved '%s' to %s", index, len(files), original_name, target)

        logger.info("[%d/%d] Extracting text from '%s'...", index, len(files), original_name)
        extracted_text, extraction_status = extract_pdf(data)
        logger.info(
            "[%d/%d] Extraction finished for '%s': status=%s, %d chars",
            index, len(files), original_name, extraction_status, len(extracted_text),
        )

        prefix = "SYN_" if source_type == "synthetic" else "REAL_"
        candidate_id = prefix + uuid.uuid4().hex[:10].upper()
        logger.info("[%d/%d] Parsing and saving CV record (candidate_id=%s)...", index, len(files), candidate_id)
        ok, reason, cv = save_cv(
            db,
            candidate_id,
            extracted_text,
            original_name,
            str(target.resolve()),
            source_type,
            Path(original_name).stem,
            extraction_status,
        )
        if not ok:
            target.unlink(missing_ok=True)
            logger.warning(
                "[%d/%d] '%s' NOT imported: reason=%s (removed stored file)",
                index, len(files), original_name, reason,
            )
        else:
            logger.info(
                "[%d/%d] '%s' imported as cv_id=%s in %.2fs",
                index, len(files), original_name, cv.id, time.perf_counter() - file_started,
            )

        items.append(
            {
                "file_name": original_name,
                "candidate_id": candidate_id,
                "cv_id": cv.id if cv else None,
                "status": "imported" if ok else "skipped",
                "reason": reason,
                "extract_status": extraction_status,
                "extracted_chars": len(extracted_text),
            }
        )
    db.commit()
    imported = sum(x["status"] == "imported" for x in items)
    skipped = sum(x["status"] != "imported" for x in items)
    logger.info(
        "Upload batch finished in %.2fs: imported=%d, skipped=%d",
        time.perf_counter() - batch_started, imported, skipped,
    )
    return {
        "imported": imported,
        "skipped": skipped,
        "items": items,
    }


@app.post("/api/cvs/import-csv")
async def import_csv(
    file: UploadFile = File(...),
    source_type: str = "synthetic",
    db: Session = Depends(get_db),
):
    rows = list(
        csv.DictReader(
            io.StringIO((await file.read()).decode("utf-8-sig", errors="ignore"))
        )
    )
    items = []
    for index, row in enumerate(rows, 1):
        text_value = (
            row.get("resume_text")
            or row.get("Resume")
            or row.get("text")
            or row.get("cv_text")
            or ""
        )
        candidate_id = row.get("candidate_id") or f"SYN_{index:05d}"
        ok, reason, cv = save_cv(
            db,
            candidate_id,
            text_value,
            file.filename,
            None,
            source_type,
            row.get("role_title") or row.get("Category") or "Candidate",
            "csv_imported",
        )
        items.append(
            {
                "candidate_id": candidate_id,
                "cv_id": cv.id if cv else None,
                "status": "imported" if ok else "skipped",
                "reason": reason,
            }
        )
    db.commit()
    return {
        "imported": sum(x["status"] == "imported" for x in items),
        "skipped": sum(x["status"] != "imported" for x in items),
        "items": items,
    }


@app.get("/api/cvs")
def list_cvs(db: Session = Depends(get_db)):
    return [cv_payload(c) for c in db.query(CV).order_by(CV.id.desc()).all()]


@app.get("/api/cvs/{cv_id}")
def get_cv(cv_id: int, db: Session = Depends(get_db)):
    cv = db.get(CV, cv_id)
    if not cv:
        raise HTTPException(404, "CV not found")
    return cv_payload(cv, include_detail=True)


@app.get("/api/cvs/{cv_id}/pdf")
def get_cv_pdf(cv_id: int, db: Session = Depends(get_db)):
    cv = db.get(CV, cv_id)
    if not cv:
        raise HTTPException(404, "CV not found")
    if not cv.file_path:
        raise HTTPException(404, "PDF file is not available for this CV")
    path = Path(cv.file_path).resolve()
    try:
        path.relative_to(UPLOAD_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(403, "Invalid PDF path") from exc
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "PDF file no longer exists")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=cv.file_name or f"cv_{cv_id}.pdf",
        content_disposition_type="inline",
    )


@app.delete("/api/cvs/{cv_id}")
def delete_cv(cv_id: int, db: Session = Depends(get_db)):
    cv = db.get(CV, cv_id)
    if not cv:
        raise HTTPException(404, "CV not found")
    db.query(ReviewerLabel).filter(ReviewerLabel.cv_id == cv_id).delete()
    if cv.file_path:
        path = Path(cv.file_path).resolve()
        try:
            path.relative_to(UPLOAD_DIR.resolve())
            path.unlink(missing_ok=True)
        except ValueError:
            pass
    db.delete(cv)
    db.commit()
    invalidate_cv_embedding_cache(cv_id)
    return {"deleted": True, "cv_id": cv_id}


@app.post("/api/jds/upload-pdfs")
async def upload_jd_pdfs(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    batch_started = time.perf_counter()
    logger.info("JD upload batch started: %d file(s)", len(files))

    items = []
    for index, upload in enumerate(files, 1):
        file_started = time.perf_counter()
        original_name = Path(upload.filename or "job_description.pdf").name
        logger.info("[%d/%d] Processing JD '%s'", index, len(files), original_name)

        if not original_name.lower().endswith(".pdf"):
            logger.warning("[%d/%d] Skipped '%s': not a PDF file", index, len(files), original_name)
            items.append(
                {"file_name": original_name, "status": "skipped", "reason": "pdf_only"}
            )
            continue

        data = await upload.read()
        if not data:
            logger.warning("[%d/%d] Skipped '%s': empty file", index, len(files), original_name)
            items.append(
                {"file_name": original_name, "status": "skipped", "reason": "empty_file"}
            )
            continue
        logger.info("[%d/%d] Read '%s' (%d bytes)", index, len(files), original_name, len(data))

        logger.info("[%d/%d] Extracting text from '%s'...", index, len(files), original_name)
        extracted_text, extraction_status = extract_pdf(data)
        normalized = clean_text(extracted_text)
        logger.info(
            "[%d/%d] Extraction finished for '%s': status=%s, %d chars",
            index, len(files), original_name, extraction_status, len(normalized),
        )

        if len(normalized) < 50:
            logger.warning("[%d/%d] Skipped '%s': extracted text too short", index, len(files), original_name)
            items.append(
                {
                    "file_name": original_name,
                    "status": "skipped",
                    "reason": "text_too_short",
                    "extract_status": extraction_status,
                }
            )
            continue

        requirements = parse_jd_requirements(normalized)
        years = extract_years(normalized)
        seniority = infer_seniority(normalized, years)
        jd = JobDescription(
            title=Path(original_name).stem[:200] or "Untitled JD",
            description=normalized[:6000],
            requirements_json=dumps(requirements),
            minimum_years=years,
            required_seniority=seniority,
        )
        db.add(jd)
        db.flush()
        hard_count = sum(1 for r in requirements if r["kind"] == "hard")
        soft_count = len(requirements) - hard_count
        logger.info(
            "[%d/%d] '%s' parsed as jd_id=%s (%d hard + %d soft requirements, %.1f yrs, %s) in %.2fs",
            index, len(files), original_name, jd.id, hard_count, soft_count, years, seniority,
            time.perf_counter() - file_started,
        )

        items.append(
            {
                "file_name": original_name,
                "jd_id": jd.id,
                "status": "imported",
                "extract_status": extraction_status,
                "hard_requirements": hard_count,
                "soft_requirements": soft_count,
            }
        )
    db.commit()
    imported = sum(x["status"] == "imported" for x in items)
    skipped = sum(x["status"] != "imported" for x in items)
    logger.info(
        "JD upload batch finished in %.2fs: imported=%d, skipped=%d",
        time.perf_counter() - batch_started, imported, skipped,
    )
    created = [
        jd_payload(db.get(JobDescription, item["jd_id"]))
        for item in items
        if item["status"] == "imported"
    ]
    return {
        "imported": imported,
        "skipped": skipped,
        "items": items,
        "jds": created,
    }


@app.post("/api/jds")
def create_jd(payload: JDCreate, db: Session = Depends(get_db)):
    jd = JobDescription(
        title=payload.title.strip(),
        description=payload.description.strip(),
        requirements_json=dumps([x.model_dump() for x in payload.requirements]),
        minimum_years=payload.minimum_years,
        required_seniority=payload.required_seniority,
    )
    db.add(jd)
    db.commit()
    db.refresh(jd)
    return jd_payload(jd)


@app.get("/api/jds")
def list_jds(db: Session = Depends(get_db)):
    return [
        jd_payload(jd)
        for jd in db.query(JobDescription).order_by(JobDescription.id.desc()).all()
    ]


@app.get("/api/jds/{jd_id}")
def get_jd(jd_id: int, db: Session = Depends(get_db)):
    jd = db.get(JobDescription, jd_id)
    if not jd:
        raise HTTPException(404, "JD not found")
    return jd_payload(jd)


@app.put("/api/jds/{jd_id}")
def update_jd(jd_id: int, payload: JDCreate, db: Session = Depends(get_db)):
    jd = db.get(JobDescription, jd_id)
    if not jd:
        raise HTTPException(404, "JD not found")
    jd.title = payload.title.strip()
    jd.description = payload.description.strip()
    jd.requirements_json = dumps([x.model_dump() for x in payload.requirements])
    jd.minimum_years = payload.minimum_years
    jd.required_seniority = payload.required_seniority
    db.commit()
    db.refresh(jd)
    return jd_payload(jd)


@app.delete("/api/jds/{jd_id}")
def delete_jd(jd_id: int, db: Session = Depends(get_db)):
    jd = db.get(JobDescription, jd_id)
    if not jd:
        raise HTTPException(404, "JD not found")
    db.query(ReviewerLabel).filter(ReviewerLabel.jd_id == jd_id).delete()
    db.delete(jd)
    db.commit()
    return {"deleted": True, "jd_id": jd_id}


@app.get("/api/experiments/methods")
def list_methods():
    return {"methods": [{"id": key, "label": label} for key, label in METHODS.items()]}


@app.post("/api/jds/{jd_id}/rank")
def do_rank(
    jd_id: int,
    top_k: int = Query(20, ge=1, le=200),
    source_type: str = Query("all", pattern="^(all|real|synthetic)$"),
    method: str = Query("full"),
    db: Session = Depends(get_db),
):
    jd = db.get(JobDescription, jd_id)
    if not jd:
        raise HTTPException(404, "JD not found")
    if method not in METHODS:
        raise HTTPException(400, f"Unknown method '{method}'. Valid values: {', '.join(METHODS)}")
    query = db.query(CV)
    if source_type != "all":
        query = query.filter(CV.source_type == source_type)
    all_cvs = query.all()
    if not all_cvs:
        raise HTTPException(400, "No CVs indexed for the selected source")
    return {
        "jd": jd_payload(jd),
        "corpus_size": len(all_cvs),
        "method": method,
        "results": rank(jd, all_cvs, top_k, method=method),
    }


@app.post("/api/labels")
def save_label(payload: LabelCreate, db: Session = Depends(get_db)):
    if not db.get(JobDescription, payload.jd_id) or not db.get(CV, payload.cv_id):
        raise HTTPException(404, "JD or CV not found")
    existing = (
        db.query(ReviewerLabel)
        .filter_by(
            jd_id=payload.jd_id,
            cv_id=payload.cv_id,
            reviewer=payload.reviewer,
        )
        .first()
    )
    if existing:
        existing.label = payload.label
        existing.note = payload.note
    else:
        db.add(ReviewerLabel(**payload.model_dump()))
    db.commit()
    return {"status": "saved"}


@app.get("/api/jds/{jd_id}/labels")
def list_labels(jd_id: int, reviewer: str | None = None, db: Session = Depends(get_db)):
    if not db.get(JobDescription, jd_id):
        raise HTTPException(404, "JD not found")
    query = db.query(ReviewerLabel).filter(ReviewerLabel.jd_id == jd_id)
    if reviewer:
        query = query.filter(ReviewerLabel.reviewer == reviewer)
    rows = query.all()
    cv_ids = {row.cv_id for row in rows}
    cvs_by_id = {
        cv.id: cv for cv in db.query(CV).filter(CV.id.in_(cv_ids)).all()
    } if cv_ids else {}
    return [
        {
            "cv_id": row.cv_id,
            "candidate_id": cvs_by_id[row.cv_id].candidate_id if row.cv_id in cvs_by_id else None,
            "reviewer": row.reviewer,
            "label": row.label,
            "note": row.note,
        }
        for row in rows
    ]


@app.get("/api/experiments/{jd_id}/metrics")
def experiment_metrics(jd_id: int, db: Session = Depends(get_db)):
    jd = db.get(JobDescription, jd_id)
    if not jd:
        raise HTTPException(404, "JD not found")
    all_cvs = db.query(CV).all()
    # Rank the entire corpus (not just a top-k slice) so every labeled CV is
    # captured regardless of where it lands -- truncating before matching
    # against labels would silently drop labeled items ranked below the cut
    # and understate recall.
    ranked = rank(jd, all_cvs, len(all_cvs))
    labels = {
        x.cv_id: x.label
        for x in db.query(ReviewerLabel).filter_by(jd_id=jd_id).all()
    }
    sequence = [labels[r["cv_id"]] for r in ranked if r["cv_id"] in labels]
    return {
        "labeled_ranked_items": len(sequence),
        "metrics": metrics(sequence) if sequence else None,
    }


EXTRACTION_PARSE_STATUS = {
    "text": "pdf_text_extracted",
    "ocr": "pdf_ocr_extracted",
}


@app.post("/api/jds/{jd_id}/experiments/compare")
def compare_experiments(
    jd_id: int,
    preview_k: int = Query(10, ge=1, le=50),
    source_type: str = Query("all", pattern="^(all|real|synthetic)$"),
    extraction: str = Query("all", pattern="^(all|text|ocr)$"),
    db: Session = Depends(get_db),
):
    """Run every baseline in the M1-M6 catalogue (thesis Table 4.x
    "Experimental model comparison") against the same CV pool so they can be
    compared side by side, scoring each against saved reviewer labels.

    Each method ranks the *entire* CV pool (not a top-k slice) before being
    scored against the labels: truncating first would silently drop whichever
    labeled CVs a given method happens to rank below the cutoff, understating
    its recall and making methods incomparable since each would be scored
    against a different subset of the labeled pool. `preview_k` only limits
    how many top-ranked rows are echoed back for display.

    `extraction` optionally narrows the pool to CVs whose text came from
    direct PDF extraction (`text`) or from the OCR fallback (`ocr`), so a
    reviewer can check whether OCR noise measurably changes ranking quality
    versus clean text-layer CVs (thesis Section 3.3 / error analysis)."""
    jd = db.get(JobDescription, jd_id)
    if not jd:
        raise HTTPException(404, "JD not found")
    query = db.query(CV)
    if source_type != "all":
        query = query.filter(CV.source_type == source_type)
    if extraction != "all":
        query = query.filter(CV.parse_status == EXTRACTION_PARSE_STATUS[extraction])
    all_cvs = query.all()
    if not all_cvs:
        raise HTTPException(400, "No CVs indexed for the selected source/extraction combination")

    labels = {
        row.cv_id: row.label
        for row in db.query(ReviewerLabel).filter_by(jd_id=jd_id).all()
    }

    results = {}
    for method_id, method_label in METHODS.items():
        ranked = rank(jd, all_cvs, len(all_cvs), method=method_id)
        sequence = [labels[r["cv_id"]] for r in ranked if r["cv_id"] in labels]
        results[method_id] = {
            "label": method_label,
            "labeled_ranked_items": len(sequence),
            "metrics": metrics(sequence) if sequence else None,
            "top": [
                {
                    "rank": r["rank"],
                    "cv_id": r["cv_id"],
                    "candidate_id": r["candidate_id"],
                    "role_title": r["role_title"],
                    "source_type": r["source_type"],
                    "baseline_score": r["baseline_score"],
                    "hard_pass": r["hard_pass"],
                    "reviewer_label": labels.get(r["cv_id"]),
                }
                for r in ranked[:preview_k]
            ],
        }

    return {
        "jd": jd_payload(jd),
        "corpus_size": len(all_cvs),
        "labeled_pairs": len(labels),
        "source_type": source_type,
        "extraction": extraction,
        "results": results,
    }
