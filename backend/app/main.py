import csv
import io
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
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
from .services.experience import extract_years, infer_seniority
from .services.ranking import rank, LOW_THRESHOLD, HIGH_THRESHOLD
from .services.metrics import metrics

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


def cv_payload(cv: CV, include_detail: bool = False) -> dict:
    result = {
        "id": cv.id,
        "candidate_id": cv.candidate_id,
        "role_title": cv.role_title,
        "source_type": cv.source_type,
        "skills": loads(cv.skills_json, []),
        "years_experience": cv.years_experience,
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

    sections = extract_sections(normalized)
    skills = extract_skills(normalized)
    years = extract_years(normalized)
    seniority = infer_seniority(normalized, years)
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
        seniority=seniority,
        parse_status=parse_status,
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
    items = []
    for upload in files:
        original_name = Path(upload.filename or "candidate.pdf").name
        if not original_name.lower().endswith(".pdf"):
            items.append(
                {"file_name": original_name, "status": "skipped", "reason": "pdf_only"}
            )
            continue

        data = await upload.read()
        if not data:
            items.append(
                {"file_name": original_name, "status": "skipped", "reason": "empty_file"}
            )
            continue

        stored_name = f"{uuid.uuid4().hex}.pdf"
        target = UPLOAD_DIR / stored_name
        target.write_bytes(data)
        extracted_text, extraction_status = extract_pdf(data)
        prefix = "SYN_" if source_type == "synthetic" else "REAL_"
        candidate_id = prefix + uuid.uuid4().hex[:10].upper()
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
    return {
        "imported": sum(x["status"] == "imported" for x in items),
        "skipped": sum(x["status"] != "imported" for x in items),
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
    return {"deleted": True, "cv_id": cv_id}


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


@app.post("/api/jds/{jd_id}/rank")
def do_rank(
    jd_id: int,
    top_k: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    jd = db.get(JobDescription, jd_id)
    if not jd:
        raise HTTPException(404, "JD not found")
    all_cvs = db.query(CV).all()
    if not all_cvs:
        raise HTTPException(400, "No CVs indexed")
    return {
        "jd": jd_payload(jd),
        "corpus_size": len(all_cvs),
        "results": rank(jd, all_cvs, top_k),
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


@app.get("/api/experiments/{jd_id}/metrics")
def experiment_metrics(jd_id: int, db: Session = Depends(get_db)):
    jd = db.get(JobDescription, jd_id)
    if not jd:
        raise HTTPException(404, "JD not found")
    ranked = rank(jd, db.query(CV).all(), 200)
    labels = {
        x.cv_id: x.label
        for x in db.query(ReviewerLabel).filter_by(jd_id=jd_id).all()
    }
    sequence = [labels[r["cv_id"]] for r in ranked if r["cv_id"] in labels]
    return {
        "labeled_ranked_items": len(sequence),
        "metrics": metrics(sequence) if sequence else None,
    }
