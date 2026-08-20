from types import SimpleNamespace
from app.services.experience import extract_years, infer_seniority, level_score
from app.services.text_processing import extract_sections, extract_skills, dumps
from app.services.ranking import assess_requirement, rank


def cv(text, years=0, seniority="unknown"):
    sections = extract_sections(text)
    return SimpleNamespace(
        id=1,
        candidate_id="C1",
        role_title="Candidate",
        source_type="test",
        clean_text=text,
        sections_json=dumps(sections),
        skills_json=dumps(extract_skills(text)),
        years_experience=years,
        seniority=seniority,
        file_name=None,
        file_path=None,
        parse_status="ok",
    )


def test_experience_functions():
    assert extract_years("5+ years of experience") == 5
    assert infer_seniority("Senior Java Developer", 6) == "senior"
    assert level_score("junior", "senior") == 0


def test_unsupported_skill_has_no_fake_evidence():
    candidate = cv("Skills\nJava Kubernetes\nExperience\nBuilt Java REST APIs.", 2, "junior")
    result = assess_requirement(
        {"text": "Kubernetes", "kind": "hard", "category": "skill"}, candidate
    )
    assert result["status"] == "unsupported"
    assert result["evidence"] is None


def test_irrelevant_best_sentence_is_not_exposed():
    candidate = cv(
        "Skills\nJava\nExperience\nWorked at IT America Inc. in Arizona City.",
        3,
        "middle",
    )
    result = assess_requirement(
        {"text": "Docker", "kind": "soft", "category": "skill"}, candidate
    )
    assert result["status"] == "not_satisfied"
    assert result["evidence"] is None


def test_seniority_constraint_reranks():
    jd = SimpleNamespace(
        title="Senior Java Developer",
        description="Java Spring Boot system design mentoring",
        requirements_json=dumps(
            [{"text": "Java", "kind": "hard", "category": "skill"}]
        ),
        minimum_years=5,
        required_seniority="senior",
    )
    junior = cv("Skills\nJava Spring Boot\nExperience\nBuilt Java APIs.", 1, "junior")
    senior = cv(
        "Skills\nJava Spring Boot\nExperience\n6 years Java. Designed production systems and mentored developers.",
        6,
        "senior",
    )
    senior.id = 2
    senior.candidate_id = "C2"
    rows = rank(jd, [junior, senior], 2)
    assert rows[0]["candidate_id"] == "C2"
    assert rows[0]["hard_pass"] is True
