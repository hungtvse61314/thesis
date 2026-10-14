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


def test_descriptor_mention_is_not_skill_evidence():
    from app.services.ranking import contains_skill_use

    assert not contains_skill_use("Led Agile delivery of a Java-based backend platform.", "java")
    assert not contains_skill_use("Managed a Docker based deployment pipeline.", "docker")
    assert contains_skill_use("Developed Java services with Spring Boot.", "java")
    assert contains_skill_use("Migrated a Java-based tool and wrote Java tests.", "java")


def test_declared_skills_are_scoped_to_skills_section():
    from app.services.ranking import ORIGINAL_CONFIG, REVISED_CONFIG, declared_skills

    candidate = cv("Skills\nScrum Jira\nExperience\nCoordinated a Java-based platform release.")
    assert "java" in declared_skills(candidate, ORIGINAL_CONFIG)
    assert "java" not in declared_skills(candidate, REVISED_CONFIG)


def test_responsibilities_demoted_to_soft():
    from app.services.ranking import ORIGINAL_CONFIG, REVISED_CONFIG, _requirements_for_jd

    jd = SimpleNamespace(
        requirements_json=dumps(
            [{"text": "Mentor junior developers", "kind": "hard", "category": "responsibility"}]
        ),
        minimum_years=0,
        required_seniority="unknown",
    )
    assert _requirements_for_jd(jd, ORIGINAL_CONFIG)[0]["kind"] == "hard"
    assert _requirements_for_jd(jd, REVISED_CONFIG)[0]["kind"] == "soft"


def test_unsupported_scores_like_not_satisfied_in_revised_config():
    from app.services.ranking import ORIGINAL_CONFIG, REVISED_CONFIG

    assert ORIGINAL_CONFIG.status_value("unsupported") == 1
    assert REVISED_CONFIG.status_value("unsupported") == 0
    assert REVISED_CONFIG.status_value("partially_satisfied") == 2
