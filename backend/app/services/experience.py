import re
from datetime import datetime

LEVELS=['intern','fresher','junior','middle','senior','lead','architect']
ALIASES={'mid':'middle','mid-level':'middle','principal':'architect','staff':'lead','entry level':'junior'}

def normalize_level(value:str)->str:
    low=(value or '').lower().strip()
    for a,b in ALIASES.items():
        if a in low: return b
    for level in LEVELS:
        if level in low: return level
    return 'unknown'

def level_score(candidate:str, required:str)->float:
    c,r=normalize_level(candidate),normalize_level(required)
    if r=='unknown': return 1.0
    if c=='unknown': return 0.5
    gap=LEVELS.index(c)-LEVELS.index(r)
    return 1.0 if gap>=0 else (0.5 if gap==-1 else 0.0)

def _detect_years(text:str, experience_text:str|None=None)->tuple[float,bool]:
    low=text.lower()
    # Allow "5+ years" and "5 + years" (a space before the plus is a common
    # resume-template variant and was previously missed entirely).
    vals=[float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)', low)]
    if vals: return max(vals), True
    # Date-range summing is scoped to Experience/Projects text when available,
    # so Education, Certification, Award, or Volunteer date ranges (e.g. an
    # MBA's start-end dates, or "Member (2018-Present)") are not counted as
    # job tenure.
    scope=(experience_text if experience_text is not None else text).lower()
    years=[]
    current=datetime.now().year
    for a,b in re.findall(r'\b(19\d{2}|20\d{2})\s*[-–—]\s*(present|current|19\d{2}|20\d{2})\b', scope):
        end=current if b in ('present','current') else int(b)
        if end>=int(a) and end-int(a)<=40: years.append(end-int(a))
    if years: return float(sum(years)), True
    return 0.0, False

def extract_years(text:str, experience_text:str|None=None)->float:
    value,_=_detect_years(text, experience_text)
    return value

def years_were_detected(text:str, experience_text:str|None=None)->bool:
    """Whether extract_years() found an explicit year phrase or date range,
    as opposed to silently defaulting to 0.0 because nothing was found."""
    _,detected=_detect_years(text, experience_text)
    return detected

def infer_seniority(text:str, years:float|None=None, scoped_text:str|None=None)->str:
    # Level keywords are searched in a narrower scope when available (Summary
    # + Experience + Projects) so a level word inside an unrelated award or
    # team name (e.g. "Junior Baseball Team", "Junior Leadership Award" in an
    # Education/Awards section) does not override the candidate's own level.
    low=(scoped_text if scoped_text is not None else text).lower()
    for level in reversed(LEVELS):
        if re.search(r'\b'+re.escape(level)+r'\b',low): return level
    y=extract_years(text) if years is None else years
    if y<1: return 'fresher'
    if y<3: return 'junior'
    if y<5: return 'middle'
    if y<8: return 'senior'
    return 'lead'
