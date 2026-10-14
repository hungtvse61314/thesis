# RAEMatch evaluation data

Data released with the thesis *AI-driven Software System for Recruitment Screening using NLP and Semantic Information Retrieval* so that the ranking-effectiveness results in Chapter 4 can be checked.

## Files

| File | Content |
|---|---|
| `relevance_labels.csv` | The 246 human relevance labels (0–3) for CV–JD pairs over the five evaluation JDs (EVAL_JD_01–05): 138 real and 108 synthetic CVs. |
| `job_descriptions.json` | The five evaluation JDs and the 11 robustness-battery JDs, with the decomposed requirement lists (`kind`: hard/soft, `category`: skill/responsibility/education) exactly as used by the ranking code. |
| `synthetic_cvs.jsonl` | Text of the 1,000 AI-generated CVs and the 27 robustness-battery CVs (one JSON object per line). All persons, contact details, and employers are fictional. |

## Columns of `relevance_labels.csv`

- `jd_id`, `jd_title`: evaluation JD (51–55).
- `cv_id`: CV id in the prototype database; it matches `cv_id` in `synthetic_cvs.jsonl` for synthetic CVs.
- `candidate_id`: `REAL_…` for real CVs, `SYN_…` for synthetic CVs.
- `cv_file_name`: for real CVs, the original file name in the Kaggle *Resume Dataset PDF* (https://www.kaggle.com/datasets/hadikp/resume-data-pdf, CC0); the real CV text is not redistributed here and can be obtained from that dataset.
- `cv_source`: `real` or `synthetic`.
- `relevance_label`: 0 not relevant, 1 weakly relevant, 2 relevant, 3 highly relevant (thesis Table 4.3). Ranking metrics treat labels ≥ 2 as relevant.
- `reviewer_note`: free-text note, where the reviewer left one.

## Known limitations

- All 246 labels were assigned by a single reviewer, using the prototype's ranking interface; no inter-annotator agreement is available.
- The model version, prompt template, and generation date used to create the synthetic CVs were not recorded, so the synthetic CVs cannot be regenerated; this file is the only copy of their text.
- See thesis Section 5.3 for the full list of limitations.

## Reproducing the results

The code is in `backend/`. The ranking configuration (thresholds and rules) is `RankConfig` in `backend/app/services/ranking.py`; the experiment scripts and their outputs are in `backend/experiments/`.
