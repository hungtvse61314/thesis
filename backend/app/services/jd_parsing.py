import re
from .text_processing import clean_text, extract_skills, split_sentences

JD_HEADINGS = {
    "mandatory": [
        "required skills", "requirements", "must have", "must-have",
        "mandatory skills", "minimum qualifications", "required qualifications",
        "core requirements",
    ],
    "optional": [
        "nice to have", "nice-to-have", "preferred skills", "preferred qualifications",
        "bonus", "optional skills", "good to have", "pluses", "plus",
    ],
    "responsibilities": [
        "responsibilities", "key responsibilities", "duties", "what you will do",
        "job responsibilities", "your role", "role and responsibilities",
    ],
    "education": [
        "education", "academic background", "education requirements",
    ],
    "certifications": [
        "certifications", "certificates", "preferred certifications",
    ],
}


def extract_jd_sections(text: str) -> dict[str, str]:
    """Same heading-detection approach as CV parsing, tuned for JD headings."""
    lines = [x.strip() for x in clean_text(text).splitlines() if x.strip()]
    sections = {k: "" for k in JD_HEADINGS}
    sections["general"] = ""
    current = "general"
    for line in lines:
        normalized = re.sub(r"[^a-z ]", "", line.lower()).strip()
        matched = None
        for key, names in JD_HEADINGS.items():
            if normalized in names or (len(normalized) < 40 and any(normalized.startswith(n) for n in names)):
                matched = key
                break
        if matched:
            current = matched
            continue
        sections[current] += (line + "\n")
    return {k: v.strip() for k, v in sections.items()}


def _list_items(text: str, limit: int) -> list[str]:
    if not text.strip():
        return []
    items = [line.strip(" -•\t*") for line in text.splitlines()]
    items = [line for line in items if len(line) >= 3]
    if len(items) <= 1:
        items = split_sentences(text)
    return items[:limit]


def parse_jd_requirements(text: str) -> list[dict]:
    """Rule-based decomposition into mandatory/optional skills, responsibilities,
    education, and certifications.

    When the JD text has no recognizable mandatory/optional heading, every
    detected skill in the whole document is treated as a mandatory requirement
    (matches the previous flat-extraction behavior) so untitled or loosely
    formatted JDs still produce usable requirements.
    """
    sections = extract_jd_sections(text)
    has_explicit_split = bool(sections["mandatory"] or sections["optional"])

    requirements: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(req_text: str, kind: str, category: str) -> None:
        req_text = req_text.strip()
        key = (req_text.lower(), category)
        if not req_text or key in seen:
            return
        seen.add(key)
        requirements.append({"text": req_text, "kind": kind, "category": category, "weight": 1.0})

    if has_explicit_split:
        mandatory_skills = extract_skills(sections["mandatory"] or text)
        optional_skills = [s for s in extract_skills(sections["optional"]) if s not in mandatory_skills]
        for skill in mandatory_skills:
            add(skill, "hard", "skill")
        for skill in optional_skills:
            add(skill, "soft", "skill")
    else:
        for skill in extract_skills(text):
            add(skill, "hard", "skill")

    for line in _list_items(sections["responsibilities"], limit=6):
        add(line, "hard", "responsibility")
    for line in _list_items(sections["education"], limit=3):
        add(line, "soft", "education")
    for line in _list_items(sections["certifications"], limit=3):
        add(line, "soft", "certification")

    return requirements
