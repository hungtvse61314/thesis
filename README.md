# RAEMatch — Defense-ready application

Full-stack prototype for requirement-aware and evidence-aware CV–JD ranking.

## Included functions

- Upload scanned or text-layer PDF CVs with OCR fallback.
- Persist original PDF files and view them inline beside requirement evidence.
- CV management: search, filter, view PDF, and delete.
- JD management: create, edit, select for ranking, and delete.
- Explicit JD selection before ranking; no implicit `jds[0]` behavior.
- Requirement-level assessment: satisfied, partially satisfied, unsupported, not satisfied.
- Seniority and minimum-experience hard constraints.
- Lexicographic ranking key and traceable evidence.
- Reviewer labels and experiment metrics API.
- Synthetic CSV import endpoint.

## Run with Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

## Run locally

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3.12 -m uvicorn app.main:app --reload --port 8000
```

OCR requires Tesseract and Poppler on the host.

### Frontend — Node.js 23.7.0

```bash
cd frontend
rm -rf node_modules
npm ci
npm run dev
```

The project uses the public npm registry through `frontend/.npmrc` and does not include `node_modules` in the archive.

## Important configuration

Evidence thresholds are currently:

- low: `0.35`
- high: `0.55`

Calibrate and freeze these values on a development set before the final thesis experiment.
