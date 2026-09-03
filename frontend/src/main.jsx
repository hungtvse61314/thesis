import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Upload,
  FileText,
  Briefcase,
  Search,
  ShieldCheck,
  AlertTriangle,
  Trash2,
  Eye,
  CheckCircle2,
  Database,
  X,
  ExternalLink,
  Pencil,
  Plus,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  FlaskConical,
  Tag,
  Play,
} from "lucide-react";
import "./style.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const SERVER_ROOT = API.replace(/\/api\/?$/, "");

async function req(path, opt = {}) {
  const response = await fetch(API + path, opt);
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the HTTP status text when the response is not JSON.
    }
    throw new Error(message);
  }
  return response.json();
}

function getPdfUrl(candidate) {
  if (!candidate?.pdf_url) return null;
  if (candidate.pdf_url.startsWith("http")) return candidate.pdf_url;
  return `${SERVER_ROOT}${candidate.pdf_url}`;
}

const emptyJd = {
  title: "Senior Java Developer",
  description: "Design production microservices, troubleshoot incidents, and mentor engineers.",
  minimum_years: 5,
  required_seniority: "senior",
  requirements:
    "Java|hard|skill\nSpring Boot|hard|skill\nSystem design|hard|responsibility\nDocker|soft|skill",
};

function requirementLines(requirements = []) {
  return requirements
    .map((item) => `${item.text}|${item.kind || "hard"}|${item.category || "skill"}`)
    .join("\n");
}

function parseRequirements(value) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [text, kind = "hard", category = "skill"] = line
        .split("|")
        .map((part) => part.trim());
      return { text, kind, category, weight: 1 };
    });
}

function CandidatePdfModal({ candidate, onClose }) {
  useEffect(() => {
    if (!candidate) return undefined;
    const onKeyDown = (event) => event.key === "Escape" && onClose();
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [candidate, onClose]);

  if (!candidate) return null;
  const pdfUrl = getPdfUrl(candidate);
  const assessments = candidate.assessments || [];

  return (
    <div className="pdf-modal-backdrop" onMouseDown={onClose}>
      <div className="pdf-modal" onMouseDown={(event) => event.stopPropagation()}>
        <div className="pdf-modal-header">
          <div>
            <h2>{candidate.role_title || candidate.candidate_id}</h2>
            <p>
              {candidate.candidate_id} · {candidate.seniority} ·{" "}
              {Number(candidate.years_experience || 0).toFixed(1)} years ·{" "}
              {candidate.source_type}
            </p>
          </div>
          <div className="pdf-modal-actions">
            {pdfUrl && (
              <a href={pdfUrl} target="_blank" rel="noreferrer" className="secondary-button">
                <ExternalLink size={17} /> Open new tab
              </a>
            )}
            <button className="icon-button" onClick={onClose} aria-label="Close CV viewer">
              <X size={22} />
            </button>
          </div>
        </div>

        <div className="pdf-modal-body">
          <aside className="candidate-review-panel">
            {candidate.rank && (
              <section className="candidate-summary-block">
                <div className="candidate-score-row">
                  <span>Rank</span>
                  <strong>#{candidate.rank}</strong>
                </div>
                <div className="candidate-score-row">
                  <span>Hard constraints</span>
                  <strong className={candidate.hard_pass ? "review-pass" : "review-fail"}>
                    {candidate.hard_pass ? "Passed" : "Gap detected"}
                  </strong>
                </div>
                <div className="candidate-score-row">
                  <span>Baseline score</span>
                  <strong>{Number(candidate.baseline_score || 0).toFixed(4)}</strong>
                </div>
              </section>
            )}

            {assessments.length > 0 && (
              <section className="review-section">
                <h3>Requirement assessment</h3>
                <div className="review-assessment-list">
                  {assessments.map((item, index) => (
                    <div
                      key={`${item.requirement}-${index}`}
                      className={`review-assessment ${item.status}`}
                    >
                      <div className="review-assessment-header">
                        <strong>{item.requirement}</strong>
                        <span>{item.status.replaceAll("_", " ")}</span>
                      </div>
                      <p>
                        {item.evidence ||
                          (item.status === "unsupported"
                            ? "Declared in Skills only. No supporting evidence was found in Experience or Projects."
                            : "No valid supporting evidence found.")}
                      </p>
                      {typeof item.score === "number" && (
                        <small>Evidence score: {Number(item.score).toFixed(4)}</small>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {candidate.ranking_key && (
              <section className="review-section">
                <h3>Ranking key</h3>
                <code className="modal-ranking-key">{JSON.stringify(candidate.ranking_key)}</code>
              </section>
            )}
          </aside>

          <section className="pdf-viewer-panel">
            {pdfUrl ? (
              <iframe
                title={`CV ${candidate.candidate_id}`}
                src={`${pdfUrl}#toolbar=1&navpanes=0&view=FitH`}
                className="pdf-frame"
              />
            ) : (
              <div className="pdf-empty-state">
                <FileText size={44} />
                <h3>PDF unavailable</h3>
                <p>This record was imported without an associated PDF file.</p>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function JdSelector({ jds, selectedJdId, onChange, onRank, cvCount, ranking, rankSource, onRankSourceChange }) {
  const selected = jds.find((item) => String(item.id) === String(selectedJdId));
  return (
    <section className="jd-selector-card">
      <div className="jd-selector-main">
        <div className="jd-selector-label">
          <Briefcase size={18} />
          <div>
            <b>Select JD for ranking</b>
            <small>The active JD controls requirements and constraints.</small>
          </div>
        </div>
        <select value={selectedJdId} onChange={(event) => onChange(event.target.value)}>
          <option value="">Select a job description</option>
          {jds.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title} · {item.required_seniority} · {item.minimum_years} years
            </option>
          ))}
        </select>
        <select value={rankSource} onChange={(event) => onRankSourceChange(event.target.value)} title="CV pool to rank within">
          <option value="all">All sources</option>
          <option value="real">Real only</option>
          <option value="synthetic">Synthetic only</option>
        </select>
        <button
          className="primary-rank-button"
          onClick={onRank}
          disabled={!selectedJdId || cvCount === 0 || ranking}
        >
          {ranking ? <RefreshCw className="spin" size={18} /> : <Search size={18} />}
          {ranking ? "Ranking..." : `Rank ${cvCount} candidates`}
        </button>
      </div>
      {selected && (
        <div className="selected-jd-preview">
          <div><span>Selected JD</span><strong>{selected.title}</strong></div>
          <div><span>Required seniority</span><strong>{selected.required_seniority}</strong></div>
          <div><span>Minimum experience</span><strong>{selected.minimum_years} years</strong></div>
          <div><span>Requirements</span><strong>{selected.requirements?.length || 0}</strong></div>
        </div>
      )}
    </section>
  );
}

function Pagination({ page, totalPages, onChange }) {
  if (totalPages <= 1) return null;
  return (
    <div className="pagination">
      <button
        className="table-icon-button"
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        title="Previous page"
      >
        <ChevronLeft size={17} />
      </button>
      <span className="pagination-status">Page {page} of {totalPages}</span>
      <button
        className="table-icon-button"
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
        title="Next page"
      >
        <ChevronRight size={17} />
      </button>
    </div>
  );
}

const PAGE_SIZE_CVS = 10;
const PAGE_SIZE_JDS = 6;

function CvManagement({ cvs, onView, onDelete }) {
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("all");
  const [seniority, setSeniority] = useState("all");
  const [page, setPage] = useState(1);
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return cvs.filter((cv) => {
      const matchesSearch =
        !query ||
        cv.candidate_id?.toLowerCase().includes(query) ||
        cv.role_title?.toLowerCase().includes(query) ||
        cv.file_name?.toLowerCase().includes(query);
      return (
        matchesSearch &&
        (source === "all" || cv.source_type === source) &&
        (seniority === "all" || cv.seniority === seniority)
      );
    });
  }, [cvs, search, source, seniority]);

  useEffect(() => {
    setPage(1);
  }, [search, source, seniority]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE_CVS));
  const safePage = Math.min(page, totalPages);
  const paged = filtered.slice((safePage - 1) * PAGE_SIZE_CVS, safePage * PAGE_SIZE_CVS);

  return (
    <section className="management-section">
      <div className="management-header">
        <div>
          <h2><span className="card-icon"><Database size={18} /></span> CV Management</h2>
          <p>Review indexed files, extraction status, source, and parsed profile.</p>
        </div>
        <div className="management-count">{filtered.length} / {cvs.length} CVs</div>
      </div>
      <div className="management-toolbar">
        <div className="search-input">
          <Search size={17} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search candidate, role, or file name"
          />
        </div>
        <select value={source} onChange={(event) => setSource(event.target.value)}>
          <option value="all">All sources</option>
          <option value="real">Real</option>
          <option value="synthetic">Synthetic</option>
        </select>
        <select value={seniority} onChange={(event) => setSeniority(event.target.value)}>
          {[
            "all", "unknown", "intern", "fresher", "junior", "middle", "senior", "lead", "architect",
          ].map((item) => (
            <option key={item} value={item}>{item === "all" ? "All seniorities" : item}</option>
          ))}
        </select>
      </div>
      <div className="data-table-wrapper">
        <table className="management-table">
          <thead>
            <tr>
              <th>Candidate</th><th>Role</th><th>Seniority</th><th>Experience</th>
              <th>Source</th><th>Extraction</th><th className="actions-col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {paged.map((cv) => (
              <tr key={cv.id}>
                <td><div className="table-primary"><strong>{cv.candidate_id}</strong><small>{cv.file_name || "No PDF file"}</small></div></td>
                <td className="role-cell" title={cv.role_title || "Unknown role"}>{cv.role_title || "Unknown role"}</td>
                <td><span className="neutral-badge">{cv.seniority || "unknown"}</span></td>
                <td>
                  {Number(cv.years_experience || 0).toFixed(1)} years
                  {!cv.years_detected && (
                    <small className="years-undetected-flag" title="No years-of-experience phrase found in CV text; this is a default, not a confirmed 0">
                      {" "}not detected
                    </small>
                  )}
                </td>
                <td><span className={`source-badge ${cv.source_type}`}>{cv.source_type}</span></td>
                <td><span className="extraction-status">{(cv.parse_status || "indexed").replaceAll("_", " ")}</span></td>
                <td className="actions-col">
                  <div className="table-actions">
                    <button className="table-icon-button" onClick={() => onView(cv)} disabled={!cv.pdf_url} title="View CV"><Eye size={17} /></button>
                    <button className="table-icon-button danger" onClick={() => onDelete(cv)} title="Delete CV"><Trash2 size={17} /></button>
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && <tr><td colSpan={7}><div className="empty-table">No CVs match the current filters.</div></td></tr>}
          </tbody>
        </table>
      </div>
      <Pagination page={safePage} totalPages={totalPages} onChange={setPage} />
    </section>
  );
}

function JdManagement({ jds, selectedJdId, onSelect, onEdit, onDelete }) {
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [jds.length]);

  const totalPages = Math.max(1, Math.ceil(jds.length / PAGE_SIZE_JDS));
  const safePage = Math.min(page, totalPages);
  const paged = jds.slice((safePage - 1) * PAGE_SIZE_JDS, safePage * PAGE_SIZE_JDS);

  return (
    <section className="management-section">
      <div className="management-header">
        <div>
          <h2><span className="card-icon"><Briefcase size={18} /></span> JD Management</h2>
          <p>Select the active JD, inspect requirements, edit, or remove obsolete records.</p>
        </div>
        <div className="management-count">{jds.length} {jds.length === 1 ? "JD" : "JDs"}</div>
      </div>
      <div className="jd-management-grid">
        {paged.map((item) => {
          const selected = String(item.id) === String(selectedJdId);
          const hard = item.requirements?.filter((requirement) => requirement.kind === "hard") || [];
          const soft = item.requirements?.filter((requirement) => requirement.kind === "soft") || [];
          return (
            <article key={item.id} className={`jd-management-card ${selected ? "selected" : ""}`}>
              <div className="jd-card-header">
                <div><span className="jd-card-label">{selected ? "Active JD" : "Job description"}</span><h3>{item.title}</h3></div>
                {selected && <CheckCircle2 size={22} className="selected-check" />}
              </div>
              <p className="jd-description">{item.description || "No description"}</p>
              <div className="jd-meta-grid">
                <div><span>Seniority</span><strong>{item.required_seniority}</strong></div>
                <div><span>Minimum years</span><strong>{item.minimum_years}</strong></div>
                <div><span>Hard requirements</span><strong>{hard.length}</strong></div>
                <div><span>Soft requirements</span><strong>{soft.length}</strong></div>
              </div>
              <div className="jd-requirement-preview">
                {item.requirements?.slice(0, 6).map((requirement, index) => (
                  <span key={`${requirement.text}-${index}`} className={requirement.kind}>{requirement.text}</span>
                ))}
                {(item.requirements?.length || 0) > 6 && <span className="more-requirements">+{item.requirements.length - 6} more</span>}
              </div>
              <div className="jd-card-actions">
                <button className={selected ? "selected-jd-button" : "select-jd-button"} onClick={() => onSelect(String(item.id))}>
                  {selected ? <><CheckCircle2 size={17} /> Selected</> : <><Search size={17} /> Use for ranking</>}
                </button>
                <button className="edit-button" onClick={() => onEdit(item)}><Pencil size={17} /> Edit</button>
                <button className="delete-button" onClick={() => onDelete(item)}><Trash2 size={17} /> Delete</button>
              </div>
            </article>
          );
        })}
        {jds.length === 0 && (
          <div className="empty-management-state"><Briefcase size={38} /><h3>No job descriptions</h3><p>Create a JD to start ranking candidates.</p></div>
        )}
      </div>
      <Pagination page={safePage} totalPages={totalPages} onChange={setPage} />
    </section>
  );
}

const RELEVANCE_LEVELS = [
  { value: 0, label: "Not relevant" },
  { value: 1, label: "Weakly relevant" },
  { value: 2, label: "Relevant" },
  { value: 3, label: "Highly relevant" },
];

function RelevanceLabelControl({ saved, onSave }) {
  const [label, setLabel] = useState(saved?.label ?? null);
  const [note, setNote] = useState(saved?.note ?? "");
  const [saving, setSaving] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);

  useEffect(() => {
    setLabel(saved?.label ?? null);
    setNote(saved?.note ?? "");
  }, [saved?.label, saved?.note]);

  const save = async () => {
    if (label === null) return;
    setSaving(true);
    try {
      await onSave(label, note);
      setSavedFlash(true);
      setTimeout(() => setSavedFlash(false), 1500);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="label-control">
      <div className="label-control-header">
        <Tag size={14} /> <span>Reviewer relevance label</span>
      </div>
      <div className="label-pills">
        {RELEVANCE_LEVELS.map((level) => (
          <button
            key={level.value}
            type="button"
            className={`label-pill ${label === level.value ? "active" : ""}`}
            onClick={() => setLabel(level.value)}
            title={level.label}
          >
            {level.value} · {level.label}
          </button>
        ))}
      </div>
      <textarea
        className="label-note"
        placeholder="Reviewer note (optional)"
        value={note}
        onChange={(event) => setNote(event.target.value)}
      />
      <button className="label-save-button" onClick={save} disabled={label === null || saving}>
        {savedFlash ? <CheckCircle2 size={15} /> : <Tag size={15} />}
        {saving ? "Saving..." : savedFlash ? "Saved" : "Save label"}
      </button>
    </div>
  );
}

const METHOD_METRIC_COLUMNS = [
  { key: "ndcg@5", label: "NDCG@5" },
  { key: "ndcg@10", label: "NDCG@10" },
  { key: "map", label: "MAP" },
  { key: "mrr", label: "MRR" },
  { key: "recall@10", label: "Recall@10" },
  { key: "recall@20", label: "Recall@20" },
];

const EXTRACTION_FILTERS = [
  { value: "all", label: "All extraction methods" },
  { value: "text", label: "Text-layer only" },
  { value: "ocr", label: "OCR-extracted only" },
];

function ExperimentsPanel({ jds, cvs, selectedJdId, onSelectJd }) {
  const [comparison, setComparison] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [sourceType, setSourceType] = useState("all");
  const [extraction, setExtraction] = useState("all");

  const scopedCvCount = useMemo(() => {
    return cvs.filter((cv) => {
      const matchesSource = sourceType === "all" || cv.source_type === sourceType;
      const matchesExtraction =
        extraction === "all" ||
        (extraction === "text" && cv.parse_status === "pdf_text_extracted") ||
        (extraction === "ocr" && cv.parse_status === "pdf_ocr_extracted");
      return matchesSource && matchesExtraction;
    }).length;
  }, [cvs, sourceType, extraction]);

  const runComparison = async () => {
    if (!selectedJdId) return setError("Select a JD first.");
    setRunning(true);
    setError("");
    try {
      const response = await req(
        `/jds/${selectedJdId}/experiments/compare?source_type=${sourceType}&extraction=${extraction}&preview_k=5`,
        { method: "POST" }
      );
      setComparison(response);
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    setComparison(null);
  }, [selectedJdId, sourceType, extraction]);

  return (
    <section className="management-section">
      <div className="management-header">
        <div>
          <h2><span className="card-icon"><FlaskConical size={18} /></span> Experiments</h2>
          <p>Run the M1-M6 baseline catalogue side by side and compare ranking metrics against saved reviewer labels.</p>
        </div>
        <div className="management-count">{scopedCvCount} CVs in scope</div>
      </div>

      <div className="experiments-toolbar">
        <select value={selectedJdId} onChange={(event) => onSelectJd(event.target.value)}>
          <option value="">Select a job description</option>
          {jds.map((item) => (
            <option key={item.id} value={item.id}>{item.title}</option>
          ))}
        </select>
        <select value={sourceType} onChange={(event) => setSourceType(event.target.value)} title="Filter by data source">
          <option value="all">All sources</option>
          <option value="real">Real only</option>
          <option value="synthetic">Synthetic only</option>
        </select>
        <select value={extraction} onChange={(event) => setExtraction(event.target.value)} title="Filter by extraction method">
          {EXTRACTION_FILTERS.map((item) => (
            <option key={item.value} value={item.value}>{item.label}</option>
          ))}
        </select>
        <button className="primary-rank-button" onClick={runComparison} disabled={!selectedJdId || running}>
          {running ? <RefreshCw className="spin" size={18} /> : <Play size={18} />}
          {running ? "Running M1-M6..." : "Run baseline comparison"}
        </button>
      </div>

      {error && <div className="message-bar error">{error}</div>}

      {comparison && (
        <>
          <div className="experiments-meta">
            <span>{comparison.labeled_pairs} labeled pair(s) used for metrics</span>
            <span>{comparison.corpus_size} candidates scored</span>
            <span>source: {comparison.source_type} · extraction: {comparison.extraction}</span>
          </div>

          {comparison.labeled_pairs === 0 && (
            <div className="message-bar">
              No reviewer labels yet for this JD — metrics below are empty. Label a few candidates in the Ranking tab, then run this comparison again.
            </div>
          )}

          <div className="data-table-wrapper">
            <table className="management-table">
              <thead>
                <tr>
                  <th>Model</th>
                  {METHOD_METRIC_COLUMNS.map((col) => <th key={col.key}>{col.label}</th>)}
                  <th>Labeled items ranked</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(comparison.results).map(([methodId, result]) => (
                  <tr key={methodId}>
                    <td><div className="table-primary"><strong>{result.label}</strong></div></td>
                    {METHOD_METRIC_COLUMNS.map((col) => (
                      <td key={col.key}>{result.metrics ? result.metrics[col.key].toFixed(4) : "—"}</td>
                    ))}
                    <td>{result.labeled_ranked_items}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="experiment-previews">
            {Object.entries(comparison.results).map(([methodId, result]) => (
              <div key={methodId} className="experiment-preview-card">
                <h4>{result.label}</h4>
                <ol>
                  {result.top.map((row) => (
                    <li key={row.cv_id}>
                      <span>{row.candidate_id}</span>
                      <small>
                        score {Number(row.baseline_score).toFixed(3)}
                        {row.hard_pass !== null && (row.hard_pass ? " · hard pass" : " · constraint gap")}
                        {row.reviewer_label !== null && row.reviewer_label !== undefined && ` · label ${row.reviewer_label}`}
                      </small>
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </>
      )}

      {!comparison && !error && (
        <div className="empty-results">
          <FlaskConical size={32} />
          <p>Select a JD and run the comparison to see TF-IDF, SBERT, section-level SBERT, requirement-aware, and the full proposed model side by side.</p>
        </div>
      )}
    </section>
  );
}

function App() {
  const [cvs, setCvs] = useState([]);
  const [jds, setJds] = useState([]);
  const [results, setResults] = useState([]);
  const [msg, setMsg] = useState("");
  const [activeTab, setActiveTab] = useState("ranking");
  const [selectedJdId, setSelectedJdId] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [jd, setJd] = useState(emptyJd);
  const [editingJdId, setEditingJdId] = useState(null);
  const [ranking, setRanking] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadSourceType, setUploadSourceType] = useState("real");
  const [rankSource, setRankSource] = useState("all");
  const [jdUploading, setJdUploading] = useState(false);
  const [jdCreateTab, setJdCreateTab] = useState("upload");
  const [reviewerName, setReviewerName] = useState(
    () => localStorage.getItem("raematch_reviewer") || "reviewer"
  );
  const [labels, setLabels] = useState({});

  useEffect(() => {
    localStorage.setItem("raematch_reviewer", reviewerName);
  }, [reviewerName]);

  const rankableCvCount = useMemo(
    () => (rankSource === "all" ? cvs.length : cvs.filter((cv) => cv.source_type === rankSource).length),
    [cvs, rankSource]
  );

  const load = async () => {
    const [cvData, jdData] = await Promise.all([req("/cvs"), req("/jds")]);
    setCvs(cvData);
    setJds(jdData);
    setSelectedJdId((current) => {
      if (current && jdData.some((item) => String(item.id) === String(current))) return current;
      return jdData.length ? String(jdData[0].id) : "";
    });
  };

  useEffect(() => {
    load().catch((error) => setMsg(error.message));
  }, []);

  const upload = async (event) => {
    const files = [...event.target.files];
    if (!files.length) return;
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    setUploading(true);
    setMsg("Processing PDFs...");
    try {
      const response = await req(`/cvs/upload-pdfs?source_type=${uploadSourceType}`, { method: "POST", body: form });
      setMsg(`${response.imported} imported, ${response.skipped} skipped`);
      await load();
    } catch (error) {
      setMsg(error.message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const uploadJdPdfs = async (event) => {
    const files = [...event.target.files];
    if (!files.length) return;
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    setJdUploading(true);
    setMsg("Extracting job descriptions from PDFs...");
    try {
      const response = await req("/jds/upload-pdfs", { method: "POST", body: form });
      setMsg(`${response.imported} JD(s) created from PDF, ${response.skipped} skipped`);
      await load();
      if (response.jds?.length === 1) {
        editJd(response.jds[0]);
      } else if (response.jds?.length > 1) {
        setSelectedJdId(String(response.jds[0].id));
        setActiveTab("jds");
      }
    } catch (error) {
      setMsg(error.message);
    } finally {
      setJdUploading(false);
      event.target.value = "";
    }
  };

  const saveJd = async () => {
    const payload = {
      ...jd,
      minimum_years: Number(jd.minimum_years),
      requirements: parseRequirements(jd.requirements),
    };
    if (!payload.title.trim() || !payload.description.trim()) {
      setMsg("JD title and description are required.");
      return;
    }
    try {
      const created = await req(editingJdId ? `/jds/${editingJdId}` : "/jds", {
        method: editingJdId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setMsg(editingJdId ? "JD updated" : "JD created");
      setSelectedJdId(String(created.id));
      setEditingJdId(null);
      setJd(emptyJd);
      await load();
    } catch (error) {
      setMsg(error.message);
    }
  };

  const editJd = (item) => {
    setJd({
      title: item.title,
      description: item.description,
      minimum_years: item.minimum_years,
      required_seniority: item.required_seniority,
      requirements: requirementLines(item.requirements),
    });
    setEditingJdId(item.id);
    setActiveTab("ranking");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const loadLabels = async (jdId) => {
    if (!jdId) return setLabels({});
    try {
      const rows = await req(`/jds/${jdId}/labels?reviewer=${encodeURIComponent(reviewerName)}`);
      const byCvId = {};
      rows.forEach((row) => { byCvId[row.cv_id] = { label: row.label, note: row.note }; });
      setLabels(byCvId);
    } catch {
      setLabels({});
    }
  };

  const saveLabel = async (cvId, label, note) => {
    await req("/labels", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jd_id: Number(selectedJdId), cv_id: cvId, reviewer: reviewerName, label, note }),
    });
    setLabels((current) => ({ ...current, [cvId]: { label, note } }));
  };

  const rankNow = async () => {
    if (!selectedJdId) return setMsg("Please select a JD before ranking.");
    if (!rankableCvCount) return setMsg("No indexed CVs are available for the selected source.");
    setRanking(true);
    setMsg("Ranking candidates...");
    try {
      const response = await req(`/jds/${selectedJdId}/rank?top_k=50&source_type=${rankSource}`, { method: "POST" });
      setResults(response.results || []);
      setMsg(`${response.results?.length || 0} candidates ranked from ${response.corpus_size} indexed CVs (${rankSource})`);
      setActiveTab("ranking");
      await loadLabels(selectedJdId);
    } catch (error) {
      setMsg(error.message);
    } finally {
      setRanking(false);
    }
  };

  const deleteCv = async (cv) => {
    if (!window.confirm(`Delete CV ${cv.candidate_id}? This action cannot be undone.`)) return;
    try {
      await req(`/cvs/${cv.id}`, { method: "DELETE" });
      setResults((current) => current.filter((item) => item.cv_id !== cv.id));
      setMsg(`CV ${cv.candidate_id} deleted`);
      await load();
    } catch (error) {
      setMsg(error.message);
    }
  };

  const deleteJd = async (item) => {
    if (!window.confirm(`Delete JD "${item.title}"?`)) return;
    try {
      await req(`/jds/${item.id}`, { method: "DELETE" });
      if (String(selectedJdId) === String(item.id)) setSelectedJdId("");
      setResults([]);
      setMsg(`JD "${item.title}" deleted`);
      await load();
    } catch (error) {
      setMsg(error.message);
    }
  };

  return (
    <>
      <header>
        <div className="brand">
          <span className="brand-mark"><Sparkles size={18} /></span>
          <div className="brand-text">
            <b>RAEMatch</b>
            <span>Requirement-aware Recruitment Screening</span>
          </div>
        </div>
        <small className="header-tag">Human-in-the-loop decision support</small>
      </header>
      <main>
        <section className="hero">
          <div>
            <span className="hero-eyebrow"><Sparkles size={13} /> AI-assisted screening</span>
            <h1>Requirement-aware, evidence-aware CV ranking</h1>
            <p>Manage real scanned CVs and job descriptions, select an active JD, and rank candidates with hard constraints, seniority alignment, and traceable evidence.</p>
          </div>
          <div className="status"><ShieldCheck /> Auditable · Deterministic · Human-in-the-loop</div>
        </section>

        <nav className="workspace-tabs">
          <button className={activeTab === "ranking" ? "active" : ""} onClick={() => setActiveTab("ranking")}><Search size={17} /> Ranking</button>
          <button className={activeTab === "cvs" ? "active" : ""} onClick={() => setActiveTab("cvs")}><Database size={17} /> CV Management <span>{cvs.length}</span></button>
          <button className={activeTab === "jds" ? "active" : ""} onClick={() => setActiveTab("jds")}><Briefcase size={17} /> JD Management <span>{jds.length}</span></button>
          <button className={activeTab === "experiments" ? "active" : ""} onClick={() => setActiveTab("experiments")}><FlaskConical size={17} /> Experiments</button>
        </nav>

        {activeTab === "ranking" && (
          <>
            <div className="grid">
              <section className="card">
                <h2><span className="card-icon"><Upload size={18} /></span> Import CVs</h2>
                <div className="field">
                  <label>Source type</label>
                  <select value={uploadSourceType} onChange={(event) => setUploadSourceType(event.target.value)} disabled={uploading}>
                    <option value="real">Real</option>
                    <option value="synthetic">Synthetic</option>
                  </select>
                </div>
                <label className={`drop ${uploading ? "busy" : ""}`}>
                  {uploading ? "Processing PDFs..." : "Select scanned or text-layer PDFs"}
                  <input type="file" multiple accept="application/pdf" onChange={upload} disabled={uploading} />
                </label>
                <div className="stat"><b>{cvs.length}</b><span>indexed CVs</span></div>
              </section>

              <section className="card">
                <h2>
                  <span className="card-icon">{editingJdId ? <Pencil size={18} /> : <Plus size={18} />}</span>
                  {editingJdId ? "Edit JD" : "Create JD"}
                </h2>
                {!editingJdId && (
                  <div className="jd-create-tabs">
                    <button
                      type="button"
                      className={jdCreateTab === "upload" ? "active" : ""}
                      onClick={() => setJdCreateTab("upload")}
                    >
                      <Upload size={15} /> Upload PDF
                    </button>
                    <button
                      type="button"
                      className={jdCreateTab === "form" ? "active" : ""}
                      onClick={() => setJdCreateTab("form")}
                    >
                      <Pencil size={15} /> Manual form
                    </button>
                  </div>
                )}

                {!editingJdId && jdCreateTab === "upload" && (
                  <>
                    <label className={`drop ${jdUploading ? "busy" : ""}`}>
                      {jdUploading ? "Extracting job descriptions..." : "Select one or more JD PDFs"}
                      <input type="file" multiple accept="application/pdf" onChange={uploadJdPdfs} disabled={jdUploading} />
                    </label>
                    <small className="jd-upload-hint">
                      Title, requirements, experience, and seniority are auto-detected from each PDF. A single upload opens directly in the Manual form tab so you can review and adjust before ranking.
                    </small>
                  </>
                )}

                {(editingJdId || jdCreateTab === "form") && (
                  <>
                    <div className="field">
                      <label>Job title</label>
                      <input value={jd.title} onChange={(event) => setJd({ ...jd, title: event.target.value })} placeholder="e.g. Senior Java Developer" />
                    </div>
                    <div className="field">
                      <label>Job description</label>
                      <textarea value={jd.description} onChange={(event) => setJd({ ...jd, description: event.target.value })} placeholder="Summarize the role, scope, and impact" />
                    </div>
                    <div className="row">
                      <div className="field">
                        <label>Minimum years</label>
                        <input type="number" min="0" value={jd.minimum_years} onChange={(event) => setJd({ ...jd, minimum_years: event.target.value })} />
                      </div>
                      <div className="field">
                        <label>Required seniority</label>
                        <select value={jd.required_seniority} onChange={(event) => setJd({ ...jd, required_seniority: event.target.value })}>
                          {["unknown", "intern", "fresher", "junior", "middle", "senior", "lead", "architect"].map((item) => <option key={item}>{item}</option>)}
                        </select>
                      </div>
                    </div>
                    <div className="field">
                      <label>Requirements</label>
                      <textarea className="requirements" value={jd.requirements} onChange={(event) => setJd({ ...jd, requirements: event.target.value })} />
                      <small className="field-hint">
                        One requirement per line — <code>text|kind|category</code>, e.g. <code>Java|hard|skill</code>. Kind is <code>hard</code> or <code>soft</code>.
                      </small>
                    </div>
                    <div className="form-actions">
                      <button onClick={saveJd}>{editingJdId ? "Update JD" : "Save JD"}</button>
                      {editingJdId && (
                        <button
                          className="secondary-form-button"
                          onClick={() => { setEditingJdId(null); setJd(emptyJd); setJdCreateTab("upload"); }}
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </>
                )}
              </section>
            </div>

            <JdSelector
              jds={jds}
              selectedJdId={selectedJdId}
              onChange={(id) => { setSelectedJdId(id); setResults([]); loadLabels(id); }}
              onRank={rankNow}
              cvCount={rankableCvCount}
              ranking={ranking}
              rankSource={rankSource}
              onRankSourceChange={(value) => { setRankSource(value); setResults([]); }}
            />

            <div className="message-bar">{msg || "Ready"}</div>

            <section className="results">
              <div className="results-heading">
                <h2>Ranked candidates</h2>
                {results.length > 0 && <span className="results-count">{results.length} candidates</span>}
                <label className="reviewer-name-field">
                  Reviewer
                  <input
                    value={reviewerName}
                    onChange={(event) => setReviewerName(event.target.value)}
                    onBlur={() => loadLabels(selectedJdId)}
                    placeholder="reviewer name"
                  />
                </label>
              </div>
              {results.map((result) => (
                <article className="candidate-card" key={result.cv_id}>
                  <div className="candidate-rank">#{result.rank}</div>
                  <div className="candidate-body">
                    <div className="candidate-heading">
                      <div>
                        <h3>{result.role_title || result.candidate_id}</h3>
                        <p className="candidate-meta">{result.candidate_id} · {result.seniority} · {Number(result.years_experience).toFixed(1)} years · {result.source_type}</p>
                      </div>
                      <div className={result.hard_pass ? "pass" : "fail"}>{result.hard_pass ? <><ShieldCheck size={15} /> Hard pass</> : <><AlertTriangle size={15} /> Constraint gap</>}</div>
                    </div>
                    <div className="chips">
                      {result.assessments.map((assessment, index) => (
                        <span key={index} className={assessment.status} title={assessment.evidence || "No valid supporting evidence"}>
                          {assessment.status.replaceAll("_", " ")}: {assessment.requirement}
                        </span>
                      ))}
                    </div>
                    <div className="candidate-actions">
                      <button className="view-cv-button" onClick={() => setSelectedCandidate(result)} disabled={!result.pdf_url}><Eye size={16} /> View CV</button>
                    </div>
                    <RelevanceLabelControl
                      saved={labels[result.cv_id]}
                      onSave={(label, note) => saveLabel(result.cv_id, label, note)}
                    />
                    <details>
                      <summary>Evidence and ranking key</summary>
                      <div className="evidence-list">
                        {result.assessments.map((assessment, index) => (
                          <div key={index} className={`evidence-item ${assessment.status}`}>
                            <div className="evidence-header"><b>{assessment.requirement}</b><span className={`evidence-status ${assessment.status}`}>{assessment.status.replaceAll("_", " ")}</span></div>
                            <div className="evidence-content">
                              {assessment.evidence || (assessment.status === "unsupported" ? "Declared in Skills only; no Experience/Project evidence found." : "No valid supporting evidence found.")}
                              <small>Evidence score: {Number(assessment.score || 0).toFixed(4)}</small>
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="ranking-key"><b>Ranking key</b><code>{JSON.stringify(result.ranking_key)}</code></div>
                    </details>
                  </div>
                </article>
              ))}
              {!results.length && <div className="empty-results"><Search size={32} /><p>Select a JD and run ranking to view candidates.</p></div>}
            </section>
          </>
        )}

        {activeTab === "cvs" && <CvManagement cvs={cvs} onView={setSelectedCandidate} onDelete={deleteCv} />}
        {activeTab === "jds" && <JdManagement jds={jds} selectedJdId={selectedJdId} onSelect={(id) => { setSelectedJdId(id); setResults([]); setMsg("JD selected for ranking"); }} onEdit={editJd} onDelete={deleteJd} />}
        {activeTab === "experiments" && (
          <ExperimentsPanel
            jds={jds}
            cvs={cvs}
            selectedJdId={selectedJdId}
            onSelectJd={(id) => setSelectedJdId(id)}
          />
        )}
      </main>
      <CandidatePdfModal candidate={selectedCandidate} onClose={() => setSelectedCandidate(null)} />
    </>
  );
}

createRoot(document.getElementById("root")).render(<App />);
