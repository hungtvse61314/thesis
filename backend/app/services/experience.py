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

def extract_years(text:str)->float:
    low=text.lower()
    vals=[float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)', low)]
    if vals: return max(vals)
    years=[]
    current=datetime.now().year
    for a,b in re.findall(r'\b(19\d{2}|20\d{2})\s*[-–—]\s*(present|current|19\d{2}|20\d{2})\b', low):
        end=current if b in ('present','current') else int(b)
        if end>=int(a) and end-int(a)<=40: years.append(end-int(a))
    return float(sum(years)) if years else 0.0

def infer_seniority(text:str, years:float|None=None)->str:
    low=text.lower()
    for level in reversed(LEVELS):
        if re.search(r'\b'+re.escape(level)+r'\b',low): return level
    y=extract_years(text) if years is None else years
    if y<1: return 'fresher'
    if y<3: return 'junior'
    if y<5: return 'middle'
    if y<8: return 'senior'
    return 'lead'
