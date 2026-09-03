import json, re, unicodedata

SKILLS=['java','spring boot','spring','python','fastapi','django','flask','javascript','typescript','react','angular','vue','node.js','nodejs','sql','mysql','postgresql','oracle','mongodb','redis','docker','kubernetes','aws','azure','gcp','kafka','rabbitmq','microservices','rest api','graphql','git','jenkins','terraform','linux','spark','hadoop','pytorch','tensorflow','selenium','cypress','jira','scrum']
HEADINGS={
 'summary':['summary','profile','career objective','objective'],
 'skills':['skills','technical skills','core competencies','technologies'],
 'experience':['experience','work experience','employment history','professional experience'],
 'projects':['projects','project experience','selected projects'],
 'education':['education','academic background'],
 'certifications':['certifications','certificates','professional certifications']}

def dumps(v): return json.dumps(v, ensure_ascii=False)
def loads(v, default):
    try: return json.loads(v or '')
    except Exception: return default

CONTROL_CHAR_RE=re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
# Boilerplate lines appended by the synthetic CV/JD generator (e.g. "Synthetic
# CV generated for academic evaluation. All names and contact details are
# fictional." / "Synthetic JD generated for academic evaluation. It does not
# represent an active vacancy."). These describe the dataset, not the
# candidate or role, so they must not be parsed as a skill, section, or
# requirement.
DISCLAIMER_RE=re.compile(
    r'(?i)\bsynthetic\s+(?:cv|jd)\s+generated for academic evaluation\.[^.]*\.'
)

def clean_text(text:str)->str:
    text=unicodedata.normalize('NFKC', text or '')
    text=CONTROL_CHAR_RE.sub(' ', text)
    text=DISCLAIMER_RE.sub(' ', text)
    text=re.sub(r'[ \t]+',' ',text)
    text=re.sub(r'\n{3,}','\n\n',text)
    return text.strip()

def split_sentences(text:str)->list[str]:
    chunks=re.split(r'(?<=[.!?])\s+|\n+', clean_text(text))
    return [c.strip(' •-\t') for c in chunks if len(c.strip())>=12]

def extract_skills(text:str)->list[str]:
    low=' '+clean_text(text).lower()+' '
    found=[]
    for s in SKILLS:
        pattern=r'(?<![a-z0-9])'+re.escape(s)+r'(?![a-z0-9])'
        if re.search(pattern, low): found.append(s)
    return sorted(set(found))

def extract_sections(text:str)->dict[str,str]:
    lines=[x.strip() for x in clean_text(text).splitlines() if x.strip()]
    sections={k:'' for k in HEADINGS}; current='summary'
    for line in lines:
        normalized=re.sub(r'[^a-z ]','',line.lower()).strip()
        matched=None
        for key, names in HEADINGS.items():
            if normalized in names or (len(normalized)<35 and any(normalized.startswith(n) for n in names)):
                matched=key; break
        if matched: current=matched; continue
        sections[current]+=(line+'\n')
    if sum(bool(v.strip()) for v in sections.values())<2:
        sections['summary']=clean_text(text)
    return {k:v.strip() for k,v in sections.items()}
