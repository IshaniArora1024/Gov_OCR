import streamlit as st
import pandas as pd
import json
import base64
import io
import re
import time
from mistralai import Mistral
MISTRAL_API_KEY = st.secrets["MISTRAL_API_KEY"]

st.set_page_config(page_title="Notify Me — Cause List Extractor", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; background-color: #0d0d0d; color: #e8e0d0; }
.stApp { background: #0d0d0d; }
h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: #e8c97a !important; }
.hero-title { font-family: 'Playfair Display', serif; font-size: 3.2rem; font-weight: 900; color: #e8c97a; letter-spacing: -1px; line-height: 1.1; margin-bottom: 0.2rem; }
.hero-sub { font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem; color: #888; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 2rem; }
.stat-card { background: #1a1a1a; border: 1px solid #2a2a2a; border-left: 3px solid #e8c97a; border-radius: 4px; padding: 1.2rem 1.5rem; text-align: center; }
.stat-number { font-family: 'Playfair Display', serif; font-size: 2.4rem; font-weight: 700; color: #e8c97a; line-height: 1; }
.stat-label { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #666; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 0.3rem; }
.court-badge { font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; background: #1a2a1a; color: #7ecb7e; padding: 4px 12px; border-radius: 2px; border: 1px solid #2a4a2a; display: inline-block; margin-bottom: 1rem; }
.step-badge { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; background: #e8c97a; color: #0d0d0d; padding: 2px 8px; border-radius: 2px; font-weight: 600; letter-spacing: 1px; }
.badge-small { font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem; padding: 1px 6px; border-radius: 2px; }
.badge-fast { background: #1a2a1a; color: #7ecb7e; border: 1px solid #2a4a2a; }
.badge-upgrade { background: #2a1a1a; color: #e87a7a; border: 1px solid #4a2a2a; }
.stButton > button { background: #e8c97a !important; color: #0d0d0d !important; border: none !important; font-family: 'IBM Plex Mono', monospace !important; font-weight: 600 !important; letter-spacing: 1.5px !important; text-transform: uppercase !important; font-size: 0.8rem !important; padding: 0.6rem 2rem !important; border-radius: 2px !important; }
.stButton > button:hover { background: #f0d898 !important; }
.divider { border: none; border-top: 1px solid #1e1e1e; margin: 1.5rem 0; }
[data-testid="stSidebar"] { background: #111 !important; border-right: 1px solid #1e1e1e !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# COURT DETECTION
# ══════════════════════════════════════════════════════════════════════════════
def detect_court(text: str) -> str:
    tl = text.lower()
    patterns = {
        "Telangana High Court":   ["telangana high court", "tshc.gov", "honourable sri justice"],
        "Delhi High Court":       ["delhi high court", "high court of delhi"],
        "Madras High Court":      ["madras high court", "high court of madras"],
        "Bombay High Court":      ["bombay high court", "high court of bombay"],
        "Calcutta High Court":    ["calcutta high court", "high court of calcutta"],
        "Supreme Court of India": ["supreme court of india"],
        "Allahabad High Court":   ["allahabad high court"],
        "Karnataka High Court":   ["karnataka high court"],
        "Kerala High Court":      ["kerala high court"],
        "Gujarat High Court":     ["gujarat high court"],
        "Rajasthan High Court":   ["rajasthan high court"],
        "Punjab & Haryana HC":    ["punjab and haryana", "punjab & haryana high court"],
        "Patna High Court":       ["patna high court"],
        "Gauhati High Court":     ["gauhati high court"],
        "Orissa High Court":      ["orissa high court"],
        "MP High Court":          ["madhya pradesh high court"],
        "Chhattisgarh HC":        ["chhattisgarh high court"],
        "Jharkhand HC":           ["jharkhand high court"],
        "Andhra Pradesh HC":      ["andhra pradesh high court"],
        "Uttarakhand HC":         ["uttarakhand high court"],
        "Himachal Pradesh HC":    ["himachal pradesh high court"],
    }
    for court, kws in patterns.items():
        if any(k in tl for k in kws):
            return court
    return "Indian High Court"


# ══════════════════════════════════════════════════════════════════════════════
# CASE NUMBER REGEX
# ══════════════════════════════════════════════════════════════════════════════
CASE_NO_RE = re.compile(
    r'\b(?:'
    r'W\.?P\.?(?:\s*\([A-Z]{1,5}\))?\s*/\s*\d{1,6}/\d{4}'
    r'|WP\s*/\s*\d{1,6}/\d{4}'
    r'|MAC(?:MA|APP|P)?\s*/\s*\d{1,6}/\d{4}'
    r'|MACMA\s*/\s*\d{1,6}/\d{4}'
    r'|C(?:RL|RM)?\.?(?:A|P|MP|MC|WP|OP|LP|RC|REV)?\.?\s*/\s*\d{1,6}/\d{4}'
    r'|C\.?S\.?(?:\s*\((?:OS|COMM)\))?\s*/\s*\d{1,6}/\d{4}'
    r'|C\.?R\.?P\.?(?:\s*\(PD\))?\s*/\s*\d{1,6}/\d{4}'
    r'|C\.?M\.?(?:A|P)?\s*/\s*\d{1,6}/\d{4}'
    r'|S\.?L\.?P\.?(?:\s*\([A-Z]{1,5}\))?\s*/\s*\d{1,6}/\d{4}'
    r'|C\.?A\.\s*/\s*\d{1,6}/\d{4}'
    r'|F\.?A\.?\s*/\s*\d{1,6}/\d{4}'
    r'|R\.?(?:F|S)\.?A\.?\s*/\s*\d{1,6}/\d{4}'
    r'|O\.?[AP]\.?\s*/\s*\d{1,6}/\d{4}'
    r'|M\.?[AF]\.?\s*/\s*\d{1,6}/\d{4}'
    r'|A\.?S\.\s*/\s*\d{1,6}/\d{4}'
    r'|CC\s*/\s*\d{1,6}/\d{4}'
    r'|X-OBJ\s*/\s*\d{1,6}/\d{4}'
    r'|ARB\.?P\.?\s*/\s*\d{1,6}/\d{4}'
    r'|EX\.?P\.?\s*/\s*\d{1,6}/\d{4}'
    r'|CONT\.?P\.?(?:\s*\([A-Z]\))?\s*/\s*\d{1,6}/\d{4}'
    r'|T\.?P\.?(?:\s*\([A-Z]\))?\s*/\s*\d{1,6}/\d{4}'
    r')',
    re.IGNORECASE
)

# Filters out IA sub-items
def get_main_case_nums(text: str) -> list[str]:
    return [
        m.group() for m in CASE_NO_RE.finditer(text)
        if not re.match(r'^IA\b', m.group(), re.I)
    ]


# ══════════════════════════════════════════════════════════════════════════════
# OCR
# ══════════════════════════════════════════════════════════════════════════════
def pdf_to_base64(f) -> str:
    return base64.standard_b64encode(f.read()).decode("utf-8")

def ocr_pdf(client, b64: str, filename: str) -> list[str]:
    if filename.lower().endswith(".pdf"):
        dtype, url = "document_url", f"data:application/pdf;base64,{b64}"
    else:
        ext  = filename.rsplit(".", 1)[-1].lower()
        mime = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png"}.get(ext,"image/png")
        dtype, url = "image_url", f"data:{mime};base64,{b64}"
    resp = client.ocr.process(
        model="mistral-ocr-latest",
        document={"type": dtype, dtype: url},
        include_image_base64=False
    )
    return [p.markdown for p in resp.pages]


# ══════════════════════════════════════════════════════════════════════════════
# SHARED EXTRACTION PROMPT
# ══════════════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """You are an expert at parsing Indian High Court cause lists.

You will receive the raw OCR text of one or more pages from a cause list.
Extract every case entry and return a JSON array only — no markdown, no backticks.

The pages may use any layout:
1. TABLE: columns separated by | (S.No | Case Number | Petitioner | Respondent | Advocates)
2. SPLIT-COLUMN: serial + party names on left side, case numbers as a separate right-side block.
   For split-column pages — match case numbers to party blocks BY ORDER (1st case num → 1st party, etc.)
3. SEQUENTIAL: serial number, case number, then party names flowing as paragraphs
4. MIXED: combination of the above

Each JSON object must have exactly these keys:
{
  "serial_number":     "1",
  "case_number":       "WP/14335/2010",
  "petitioner":        "Name of petitioner",
  "respondent":        "Name of respondent",
  "lawyer_petitioner": "Advocate name or null",
  "lawyer_respondent": "Advocate name or null",
  "hearing_date":      "05/03/2026 or null"
}

RULES:
- Section headers (FOR ADMISSION, FOR ORDERS, FINAL HEARING, PRONOUNCEMENT, etc.) are NOT cases — skip
- IA / Interlocutory Application numbers are sub-items — do NOT make rows for them
- If a party block has no visible case number → case_number: null, still include the row
- Multiple advocates → join with " & ". Include role labels like (SC FOR EPFO), GP FOR HOME
- Return [] for header-only or blank pages"""


# ══════════════════════════════════════════════════════════════════════════════
# ADAPTIVE EXTRACTION ENGINE
#
# Phase 1 — Fast path: group 2 pages per call using mistral-small
#            Target: ~2-3x faster than v4, same accuracy on clean layouts
#
# Phase 2 — Upgrade path: triggered per-page only when Phase 1 yield is low
#            (<80% of case numbers found by regex vs extracted by LLM)
#            Uses mistral-large + reconciliation call for that specific page only
#
# Result: clean pages finish in ~1 sec each (small model, 2-page batches)
#         only messy pages pay the large model + reconciliation cost
# ══════════════════════════════════════════════════════════════════════════════

SMALL_MODEL = "mistral-small-latest"
LARGE_MODEL = "mistral-large-latest"
ACCURACY_THRESHOLD = 0.80   # upgrade if extracted < 80% of regex-found case nums


def call_llm(client, model: str, pages_text: str, court: str, label: str) -> list[dict]:
    """Single LLM call. Returns parsed list of case dicts."""
    try:
        resp = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f"Court: {court}\n{label}\n\n{pages_text}"}
            ],
            temperature=0.0,
            max_tokens=5000
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"```json\s*|```", "", raw).strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r'\[.*\]', raw, re.DOTALL)
            parsed = json.loads(m.group()) if m else []
        if isinstance(parsed, dict):
            parsed = [parsed]
        return parsed if isinstance(parsed, list) else []
    except Exception as e:
        st.warning(f"LLM call failed ({label}): {str(e)[:100]}")
        return []


def extraction_accuracy(page_text: str, cases: list[dict]) -> float:
    """
    Returns ratio: extracted case nums / regex-found case nums on page.
    1.0 = perfect. Below ACCURACY_THRESHOLD = needs upgrade.
    """
    found_on_page = set(cn.upper() for cn in get_main_case_nums(page_text))
    if not found_on_page:
        return 1.0   # no case numbers detectable by regex → can't measure, assume OK
    extracted = set(
        str(c.get("case_number") or "").strip().upper()
        for c in cases if c.get("case_number")
    )
    matched = found_on_page & extracted
    return len(matched) / len(found_on_page)


def reconcile_page(client, page_text: str, cases: list[dict],
                   court: str, page_num: int) -> list[dict]:
    """
    Called only when large-model extraction still has gaps.
    Targeted: tells the model exactly which case numbers are missing.
    """
    found_on_page = set(cn.upper() for cn in get_main_case_nums(page_text))
    extracted_nums = set(
        str(c.get("case_number") or "").strip().upper()
        for c in cases if c.get("case_number")
    )
    missing = found_on_page - extracted_nums
    if not missing:
        return cases

    prompt = (
        f"Court: {court}\nPage {page_num}\n\n"
        f"These case numbers are on the page but were NOT extracted:\n"
        + "\n".join(sorted(missing)) +
        f"\n\nFind each one in the page text below and return ONLY the missing entries as a JSON array.\n\n"
        f"Page text:\n{page_text}"
    )
    try:
        resp = client.chat.complete(
            model=LARGE_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.0,
            max_tokens=2000
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"```json\s*|```", "", raw).strip()
        recovered = json.loads(raw) if raw.startswith('[') else []
        if isinstance(recovered, list):
            cases = cases + recovered
    except Exception:
        pass
    return cases


def adaptive_extract(client, page_texts: list[str], court: str,
                     progress_bar, status_el) -> tuple[list[dict], list[dict]]:
    """
    Returns (all_cases, page_stats) where page_stats is for the debug table.
    """
    all_cases  = []
    page_stats = []

    # ── Phase 1: fast pass — 2 pages per call, mistral-small ─────────────────
    PAGE_BATCH = 2
    batches = [page_texts[i:i+PAGE_BATCH] for i in range(0, len(page_texts), PAGE_BATCH)]

    page_results = {}   # page_index → list[dict]

    for b_idx, batch in enumerate(batches):
        pct = 32 + int(((b_idx + 1) / len(batches)) * 40)
        progress_bar.progress(pct)
        first_page = b_idx * PAGE_BATCH + 1
        last_page  = min(first_page + PAGE_BATCH - 1, len(page_texts))
        status_el.markdown(
            f'<span class="step-badge">03</span> &nbsp;'
            f'<span class="badge-small badge-fast">SMALL</span> &nbsp;'
            f'Pages {first_page}–{last_page} of {len(page_texts)}',
            unsafe_allow_html=True
        )

        batch_text   = "\n\n--- PAGE BREAK ---\n\n".join(batch)
        label        = f"Pages {first_page}–{last_page}"
        batch_cases  = call_llm(client, SMALL_MODEL, batch_text, court, label)

        # Assign extracted cases back to individual pages by serial/case proximity
        # Simple approach: split cases roughly by page break marker count
        for i, page_text in enumerate(batch):
            page_idx = b_idx * PAGE_BATCH + i
            # Cases that mention case numbers found on this page
            page_case_nums = set(cn.upper() for cn in get_main_case_nums(page_text))
            if page_case_nums:
                page_cases = [
                    c for c in batch_cases
                    if str(c.get("case_number") or "").upper() in page_case_nums
                ]
                # Any cases with null case_number: assign to first page of batch
                if i == 0:
                    null_cases = [c for c in batch_cases if not c.get("case_number")]
                    page_cases = page_cases + null_cases
            else:
                page_cases = batch_cases if i == 0 else []
            page_results[page_idx] = page_cases

    # ── Phase 2: upgrade only low-accuracy pages ──────────────────────────────
    upgrade_count = 0
    for page_idx, page_text in enumerate(page_texts):
        cases    = page_results.get(page_idx, [])
        accuracy = extraction_accuracy(page_text, cases)
        found_on_page = get_main_case_nums(page_text)

        if accuracy < ACCURACY_THRESHOLD and found_on_page:
            upgrade_count += 1
            pct = 72 + int((page_idx / len(page_texts)) * 15)
            progress_bar.progress(min(pct, 87))
            status_el.markdown(
                f'<span class="step-badge">03b</span> &nbsp;'
                f'<span class="badge-small badge-upgrade">LARGE</span> &nbsp;'
                f'Upgrading page {page_idx+1} '
                f'(accuracy {accuracy:.0%} → retrying with large model)',
                unsafe_allow_html=True
            )
            # Re-extract with large model
            upgraded = call_llm(client, LARGE_MODEL, page_text, court,
                                 f"Page {page_idx+1}")
            upgraded_accuracy = extraction_accuracy(page_text, upgraded)

            # Reconcile if still gaps
            if upgraded_accuracy < ACCURACY_THRESHOLD:
                upgraded = reconcile_page(client, page_text, upgraded,
                                          court, page_idx + 1)

            page_results[page_idx] = upgraded

        # Build stats
        final_cases   = page_results.get(page_idx, [])
        final_accuracy = extraction_accuracy(page_text, final_cases)
        page_stats.append({
            "page":      page_idx + 1,
            "cases":     len(final_cases),
            "accuracy":  f"{final_accuracy:.0%}",
            "model":     "large+reconcile" if accuracy < ACCURACY_THRESHOLD else "small",
        })
        all_cases.extend(page_results.get(page_idx, []))

    return all_cases, page_stats, upgrade_count


# ══════════════════════════════════════════════════════════════════════════════
# DEDUPLICATION
# ══════════════════════════════════════════════════════════════════════════════
def deduplicate(cases: list[dict]) -> list[dict]:
    seen_cn, seen_sn, result = set(), set(), []
    for c in cases:
        cn = str(c.get("case_number") or "").strip().upper()
        sn = str(c.get("serial_number") or "").strip()
        if cn and cn not in {"NULL","NONE",""}:
            if cn in seen_cn: continue
            seen_cn.add(cn)
        elif sn:
            if sn in seen_sn: continue
            seen_sn.add(sn)
        result.append(c)

    def key(c):
        try:    return int(str(c.get("serial_number") or "0").strip())
        except: return 9999
    result.sort(key=key)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT
# ══════════════════════════════════════════════════════════════════════════════
def to_df(cases):
    if not cases: return pd.DataFrame()
    return pd.DataFrame([{
        "Sr. No":              c.get("serial_number",""),
        "Case Number":         c.get("case_number",""),
        "Petitioner":          c.get("petitioner",""),
        "Respondent":          c.get("respondent",""),
        "Lawyer (Petitioner)": c.get("lawyer_petitioner",""),
        "Lawyer (Respondent)": c.get("lawyer_respondent",""),
        "Hearing Date":        c.get("hearing_date",""),
    } for c in cases]).fillna("")

def to_excel(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Cause List")
        ws = w.sheets["Cause List"]
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(
                max(len(str(c.value or "")) for c in col) + 4, 50)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div style="font-family:serif;font-size:1.5rem;font-weight:900;color:#e8c97a;">⚖️ Notify Me</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:monospace;font-size:0.7rem;color:#555;letter-spacing:2px;text-transform:uppercase;margin-bottom:1rem;">Cause List Extractor v5</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""
    <div style="font-family:monospace;font-size:0.65rem;color:#555;line-height:2.2;">
    ADAPTIVE ENGINE v5<br>
    ✓ Phase 1 — mistral-small<br>
    &nbsp;&nbsp;2 pages/call, fast path<br>
    ✓ Phase 2 — mistral-large<br>
    &nbsp;&nbsp;only on low-accuracy pages<br>
    ✓ Reconciliation only if needed<br>
    ✓ No layout preprocessing<br>
    ✓ Works on all court layouts<br><br>
    TYPICAL SPEED<br>
    ✓ Clean PDF: ~45–90 sec<br>
    ✓ Mixed/messy: ~2–3 min<br><br>
    OUTPUT<br>
    ✓ Sr. No · Case Number<br>
    ✓ Petitioner · Respondent<br>
    ✓ Lawyer (Pet) · Lawyer (Res)<br>
    ✓ Hearing Date<br><br>
    SUPPORTED<br>
    ✓ All 25 Indian High Courts<br>
    ✓ Supreme Court of India<br>
    ✓ Digital &amp; scanned PDFs<br>
    ✓ JPG / PNG · Up to 100 pages
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN UI
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="hero-title">Cause List Extractor</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Adaptive · Fast on Clean · Precise on Messy · All 25 Indian High Courts</div>', unsafe_allow_html=True)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

col_up, col_info = st.columns([2, 1])
with col_up:
    st.markdown('<span class="step-badge">UPLOAD</span>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload cause list",
                                     type=["pdf","png","jpg","jpeg"],
                                     label_visibility="collapsed")
with col_info:
    st.markdown("""
    <div style="font-family:monospace;font-size:0.72rem;color:#555;line-height:2.2;margin-top:0.3rem;">
    ✓ Digital PDF · Scanned PDF<br>
    ✓ JPG / PNG<br>
    ✓ Up to 100 pages<br>
    ✓ Any court format
    </div>""", unsafe_allow_html=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Button row: Extract + Clear ───────────────────────────────────────────────
btn_col, clear_col = st.columns([3, 1])
with btn_col:
    process_btn = st.button("⚡  Extract All Cases", use_container_width=True)
with clear_col:
    if st.button("🗑 Clear", use_container_width=True):
        for k in ["results", "page_texts", "fname"]:
            st.session_state.pop(k, None)
        st.rerun()

# ── Run extraction only when button pressed — store everything in session_state
if process_btn:
    if not uploaded_file:
        st.warning("Please upload a cause list first.")
    else:
        try:
            client   = Mistral(api_key=MISTRAL_API_KEY)
            progress = st.progress(0)
            status   = st.empty()
            t_start  = time.time()

            status.markdown('<span class="step-badge">01</span> &nbsp; Running Mistral OCR...', unsafe_allow_html=True)
            progress.progress(5)
            b64        = pdf_to_base64(uploaded_file)
            page_texts = ocr_pdf(client, b64, uploaded_file.name)
            progress.progress(30)

            full_text      = "\n".join(page_texts)
            detected_court = detect_court(full_text)
            status.markdown(
                f'<span class="step-badge">02</span> &nbsp;'
                f'<b style="color:#7ecb7e">{detected_court}</b> &nbsp;'
                f'<span style="color:#555;font-size:0.7rem;font-family:monospace;">{len(page_texts)} pages</span>',
                unsafe_allow_html=True
            )
            progress.progress(32)
            time.sleep(0.3)

            raw_cases, page_stats, upgrades = adaptive_extract(
                client, page_texts, detected_court, progress, status
            )
            progress.progress(90)

            status.markdown('<span class="step-badge">04</span> &nbsp; Finalising...', unsafe_allow_html=True)
            final_cases = deduplicate(raw_cases)
            df          = to_df(final_cases)
            elapsed     = time.time() - t_start

            progress.progress(100)
            time.sleep(0.2)
            status.empty()
            progress.empty()

            # ── Save everything to session_state — no re-run will re-call APIs
            st.session_state["results"] = {
                "final_cases":     final_cases,
                "df":              df,
                "page_stats":      page_stats,
                "detected_court":  detected_court,
                "elapsed":         elapsed,
                "upgrades":        upgrades,
            }
            st.session_state["page_texts"] = page_texts
            st.session_state["fname"]      = uploaded_file.name.rsplit(".", 1)[0]

        except Exception as e:
            st.error(f"Error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# ── Render results from session_state (survives all button clicks / downloads)
if "results" in st.session_state:
    r          = st.session_state["results"]
    df         = r["df"]
    final_cases= r["final_cases"]
    page_stats = r["page_stats"]
    court      = r["detected_court"]
    elapsed    = r["elapsed"]
    upgrades   = r["upgrades"]
    page_texts = st.session_state.get("page_texts", [])
    fname      = st.session_state.get("fname", "extracted")

    if df.empty:
        st.warning("No cases found.")
    else:
        st.markdown(f'<div class="court-badge">🏛 {court}</div>', unsafe_allow_html=True)
        st.success(
            f"✅ Extracted **{len(df)} cases** from **{len(page_texts)} pages** "
            f"in **{elapsed:.0f}s** "
            f"({'small only' if upgrades == 0 else f'{upgrades} pages upgraded to large'})"
        )

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="stat-card"><div class="stat-number">{len(df)}</div><div class="stat-label">Total Cases</div></div>', unsafe_allow_html=True)
        with c2:
            lp = df["Lawyer (Petitioner)"].replace("", pd.NA).dropna()
            st.markdown(f'<div class="stat-card"><div class="stat-number">{len(lp)}</div><div class="stat-label">Lawyers Found</div></div>', unsafe_allow_html=True)
        with c3:
            dt = df["Hearing Date"].replace("", pd.NA).dropna()
            st.markdown(f'<div class="stat-card"><div class="stat-number">{len(dt)}</div><div class="stat-label">Dates Found</div></div>', unsafe_allow_html=True)
        with c4:
            filled = df.replace("", pd.NA).notna().sum().sum()
            pct = int(filled / df.size * 100) if df.size else 0
            st.markdown(f'<div class="stat-card"><div class="stat-number">{pct}%</div><div class="stat-label">Fill Rate</div></div>', unsafe_allow_html=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:monospace;font-size:0.75rem;color:#e8c97a;text-transform:uppercase;letter-spacing:2px;margin-bottom:0.5rem;">Extracted Cases</div>', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, height=420)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        d1, d2, d3 = st.columns(3)
        with d1:
            st.download_button("📥 Excel", data=to_excel(df),
                file_name=f"{fname}_extracted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)
        with d2:
            st.download_button("📥 JSON",
                data=json.dumps(final_cases, indent=2, ensure_ascii=False),
                file_name=f"{fname}_extracted.json", mime="application/json",
                use_container_width=True)
        with d3:
            st.download_button("📥 CSV", data=df.to_csv(index=False),
                file_name=f"{fname}_extracted.csv", mime="text/csv",
                use_container_width=True)

        with st.expander("📄 Per-page stats"):
            st.dataframe(pd.DataFrame(page_stats), use_container_width=True)

        if page_texts:
            with st.expander("🔍 Raw OCR — page viewer"):
                pg = st.selectbox("Page", range(1, len(page_texts)+1), key="pg")
                st.text_area("OCR text", page_texts[pg-1], height=350)

elif not process_btn:
    st.markdown("""
    <div style="text-align:center;padding:4rem 0;">
        <div style="font-size:4rem;margin-bottom:1rem;">⚖️</div>
        <div style="font-family:monospace;font-size:0.8rem;color:#333;letter-spacing:3px;">
            UPLOAD A CAUSE LIST TO BEGIN
        </div>
    </div>""", unsafe_allow_html=True)