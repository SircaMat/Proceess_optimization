import streamlit as st
from bs4 import BeautifulSoup
import json
from pathlib import Path
from typing import Dict, Optional

# =====================================================
# Config
# =====================================================
st.set_page_config(page_title="HTML Slide Editor (IRRBB)", layout="wide")
st.title("Process AS_IS-TO_BE HTML slide editor")
st.caption("Upload a template-based HTML slide, edit fields, translate headings & content, and export. Built to handle re-uploads safely.")

# =====================================================
# Constants & helpers
# =====================================================
FIELD_KEYS = [
    "title", "left_label", "right_label",
    "left_people", "left_process", "left_technology", "left_data", "left_output",
    "right_people", "right_process", "right_technology", "right_data", "right_output",
    "page_number", "footer_summary",
]

STATE_FILE = Path("streamlit_irrbb_state.json")

DEFAULTS: Dict[str, str] = {k: "TBD" for k in FIELD_KEYS}
DEFAULTS.update({
    "page_number": "1",
    "left_label": "AS-IS (danes)",
    "right_label": "Ambicija (to-be)",
    "footer_summary": "Digitalizacija in centralizacija procesa z avtomatskimi kontrolami.",
})

FALLBACK_HTML = """
<!DOCTYPE html><html lang=\"sl\"><head><meta charset=\"utf-8\"><title>{{title}}</title></head>
<body><h1>{{title}}</h1>
<div class=\"panel left\"><div class=\"side-label\"><span class=\"tag\">{{left_label}}</span></div>
<div class=\"section\"><h3>Ljudje:</h3><p>{{left_people}}</p></div>
<div class=\"section\"><h3>Proces:</h3><p>{{left_process}}</p></div>
<div class=\"section\"><h3>Tehnologija:</h3><p>{{left_technology}}</p></div>
<div class=\"section\"><h3>Podatki:</h3><p>{{left_data}}</p></div>
<div class=\"section\"><h3>Output:</h3><p>{{left_output}}</p></div></div>
<div class=\"panel right\"><div class=\"side-label\"><span class=\"tag\">{{right_label}}</span></div>
<div class=\"section\"><h3>Ljudje:</h3><p>{{right_people}}</p></div>
<div class=\"section\"><h3>Proces:</h3><p>{{right_process}}</p></div>
<div class=\"section\"><h3>Tehnologija:</h3><p>{{right_technology}}</p></div>
<div class=\"section\"><h3>Podatki:</h3><p>{{right_data}}</p></div>
<div class=\"section\"><h3>Output:</h3><p>{{right_output}}</p></div></div>
<footer><span class=\"pagenum\">{{page_number}}</span> <strong>{{footer_summary}}</strong></footer>
</body></html>
"""

# Static labels used in the HTML template (section headings)
STATIC_LABELS = {
    "sl": {
        "people": "Ljudje:",
        "process": "Proces:",
        "technology": "Tehnologija:",
        "data": "Podatki:",
        "output": "Output:",
    },
    "en": {
        "people": "People:",
        "process": "Process:",
        "technology": "Technology:",
        "data": "Data:",
        "output": "Output:",
    },
}

# =====================================================
# Translation (best effort)
# =====================================================
@st.cache_data(show_spinner=False)
def _get_translator_or_none():
    try:
        from deep_translator import GoogleTranslator  # optional dep
        return GoogleTranslator
    except Exception:
        return None


def translate_text(txt: str, src: str, dest: str) -> str:
    if not txt:
        return txt
    GT = _get_translator_or_none()
    if GT is None or src == dest:
        return txt
    try:
        return GT(source=src, target=dest).translate(txt)
    except Exception:
        # Fail safe: just return original
        return txt


# =====================================================
# HTML parsing & synthesis
# =====================================================

def parse_html_fields(html: str) -> Dict[str, str]:
    """Parse fields from a slide HTML based on the known template structure."""
    soup = BeautifulSoup(html, "html.parser")

    def get_text(selector: str) -> str:
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else ""

    left_sections = soup.select(".panel.left .section p")
    right_sections = soup.select(".panel.right .section p")

    def sec(idx: int, arr):
        return arr[idx].get_text(strip=True) if len(arr) > idx else ""

    fields: Dict[str, str] = {
        "title": get_text("h1"),
        "left_label": get_text(".panel.left .side-label .tag"),
        "right_label": get_text(".panel.right .side-label .tag"),
        "left_people": sec(0, left_sections),
        "left_process": sec(1, left_sections),
        "left_technology": sec(2, left_sections),
        "left_data": sec(3, left_sections),
        "left_output": sec(4, left_sections),
        "right_people": sec(0, right_sections),
        "right_process": sec(1, right_sections),
        "right_technology": sec(2, right_sections),
        "right_data": sec(3, right_sections),
        "right_output": sec(4, right_sections),
        "page_number": get_text("footer .pagenum"),
        "footer_summary": get_text("footer strong"),
    }

    for k in FIELD_KEYS:
        if not fields.get(k):
            fields[k] = DEFAULTS.get(k, "TBD")
    return fields


def apply_fields_to_html(original_html: str, fields: Dict[str, str], label_lang: Optional[str] = None) -> str:
    """Apply field values and static label language to the uploaded HTML."""
    soup = BeautifulSoup(original_html, "html.parser")

    # Optionally set the document language attribute
    if label_lang in ("sl", "en") and soup.html is not None:
        soup.html["lang"] = label_lang

    def set_text(selector: str, value: str) -> None:
        el = soup.select_one(selector)
        if el is not None:
            el.string = value

    # Title & side labels
    set_text("h1", fields["title"])  # title
    set_text(".panel.left .side-label .tag", fields["left_label"])  # left label
    set_text(".panel.right .side-label .tag", fields["right_label"])  # right label

    # Sections (content)
    def set_sec(panel_sel: str, idx: int, value: str) -> None:
        ps = soup.select(f"{panel_sel} .section p")
        if len(ps) > idx and ps[idx] is not None:
            ps[idx].string = value

    set_sec(".panel.left", 0, fields["left_people"])
    set_sec(".panel.left", 1, fields["left_process"])
    set_sec(".panel.left", 2, fields["left_technology"])
    set_sec(".panel.left", 3, fields["left_data"])
    set_sec(".panel.left", 4, fields["left_output"])

    set_sec(".panel.right", 0, fields["right_people"])
    set_sec(".panel.right", 1, fields["right_process"])
    set_sec(".panel.right", 2, fields["right_technology"])
    set_sec(".panel.right", 3, fields["right_data"])
    set_sec(".panel.right", 4, fields["right_output"])

    # Static section headings (translate field NAMES on the slide)
    if label_lang in STATIC_LABELS:
        labels = STATIC_LABELS[label_lang]
        left_h3s = soup.select(".panel.left .section h3")
        right_h3s = soup.select(".panel.right .section h3")
        desired = [
            labels["people"],
            labels["process"],
            labels["technology"],
            labels["data"],
            labels["output"],
        ]
        for idx, text in enumerate(desired):
            if len(left_h3s) > idx and left_h3s[idx]:
                left_h3s[idx].string = text
            if len(right_h3s) > idx and right_h3s[idx]:
                right_h3s[idx].string = text

    # Footer
    set_text("footer .pagenum", fields["page_number"])  # page number
    set_text("footer strong", fields["footer_summary"])  # summary

    return str(soup)


# =====================================================
# Persistence helpers
# =====================================================

def load_persisted() -> Optional[Dict[str, str]]:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def persist(fields: Dict[str, str]) -> None:
    try:
        STATE_FILE.write_text(
            json.dumps(fields, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


# =====================================================
# Session-state management
# =====================================================

def init_fields(fields: Dict[str, str]) -> None:
    """Force-initialize widget state from given fields (overwrites existing)."""
    for k in FIELD_KEYS:
        st.session_state[k] = fields.get(k, DEFAULTS.get(k, ""))
    st.session_state["fields_obj"] = {k: st.session_state[k] for k in FIELD_KEYS}


def clear_widget_state() -> None:
    for k in list(st.session_state.keys()):
        if k in FIELD_KEYS:
            st.session_state.pop(k)


# =====================================================
# Sidebar: Upload / Persistence / Translate / Utilities
# =====================================================
with st.sidebar:
    st.header("Upload")
    uploaded = st.file_uploader(
        "Upload HTML slide", type=["html", "htm"], accept_multiple_files=False
    )
    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        new_hash = hash(file_bytes)
        if st.session_state.get("_upload_hash") != new_hash:
            html = file_bytes.decode("utf-8", errors="ignore")
            st.session_state["base_html"] = html
            parsed = parse_html_fields(html)
            clear_widget_state()
            init_fields(parsed)
            st.session_state["_upload_hash"] = new_hash
            st.success("Parsed uploaded HTML and refreshed widget values.")

    st.header("Persistence")
    col_s, col_l = st.columns(2)
    with col_s:
        if st.button("💾 Save fields", use_container_width=True):
            persist({k: st.session_state.get(k, DEFAULTS.get(k, "")) for k in FIELD_KEYS})
            st.toast("Saved locally (streamlit_irrbb_state.json)")
    with col_l:
        if st.button("📥 Load fields", use_container_width=True):
            data = load_persisted()
            if data:
                clear_widget_state()
                init_fields({k: data.get(k, DEFAULTS.get(k, "")) for k in FIELD_KEYS})
                st.toast("Loaded saved fields")
            else:
                st.info("No local state found.")

    st.header("Translate")
    lang = st.radio("Translate to", ["sl", "en"], horizontal=True, key="_lang")
    if st.button("🌐 Translate current fields", use_container_width=True):
        src = "sl" if lang == "en" else "en"
        translated = {k: translate_text(st.session_state.get(k, ""), src, lang) for k in FIELD_KEYS}
        init_fields(translated)
        # Remember chosen label language for static headings & set HTML lang
        st.session_state["_label_lang"] = lang
        st.toast(f"Translated UI labels + fields to {lang.upper()} (best-effort)")

    st.header("Utilities")
    if st.button("🧹 Clear all fields", use_container_width=True):
        clear_widget_state()
        init_fields({k: "" for k in FIELD_KEYS})
        st.session_state["base_html"] = FALLBACK_HTML
        st.session_state["_upload_hash"] = None
        st.toast("Cleared fields and reset base HTML")


# =====================================================
# Base HTML for preview/export & first-time init
# =====================================================
base_html = st.session_state.get("base_html", FALLBACK_HTML)
if not any(k in st.session_state for k in FIELD_KEYS):
    init_fields(DEFAULTS.copy())


# =====================================================
# Editor form (widgets bind to session_state keys)
# =====================================================
with st.form("editor_form", clear_on_submit=False):
    st.subheader("Editable fields")

    st.text_input("Title", key="title")

    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Left label", key="left_label")
        st.text_area("Left – People", key="left_people")
        st.text_area("Left – Process", key="left_process")
        st.text_area("Left – Technology", key="left_technology")
        st.text_area("Left – Data", key="left_data")
        st.text_area("Left – Output", key="left_output")
    with c2:
        st.text_input("Right label", key="right_label")
        st.text_area("Right – People", key="right_people")
        st.text_area("Right – Process", key="right_process")
        st.text_area("Right – Technology", key="right_technology")
        st.text_area("Right – Data", key="right_data")
        st.text_area("Right – Output", key="right_output")

    c3, c4 = st.columns([1, 3])
    with c3:
        st.text_input("Page number", key="page_number")
    with c4:
        st.text_input("Footer summary", key="footer_summary")

    submitted = st.form_submit_button("✅ Apply changes to preview", use_container_width=True)
    if submitted:
        st.toast("Applied changes")


# =====================================================
# Live preview & export
# =====================================================
current = {k: st.session_state.get(k, DEFAULTS.get(k, "")) for k in FIELD_KEYS}
label_lang = st.session_state.get("_label_lang", "sl")
preview_html = apply_fields_to_html(base_html, current, label_lang=label_lang)

st.subheader("Preview")
st.components.v1.html(preview_html, height=900, scrolling=True)

st.download_button(
    label="⬇️ Download updated HTML",
    file_name="edited_slide.html",
    mime="text/html",
    data=preview_html.encode("utf-8"),
    use_container_width=True,
)

# Import/Export field JSON
st.divider()
st.subheader("Import/Export field values")
colA, colB = st.columns(2)
with colA:
    saved_json = st.file_uploader("Import fields JSON", type=["json"], key="import_json")
    if saved_json is not None:
        try:
            data = json.load(saved_json)
            clear_widget_state()
            init_fields({k: data.get(k, DEFAULTS.get(k, "")) for k in FIELD_KEYS})
            st.success("Imported fields from JSON.")
        except Exception as e:
            st.error(f"Failed to import JSON: {e}")
with colB:
    st.download_button(
        label="Export current fields (JSON)",
        file_name="fields_export.json",
        mime="application/json",
        data=json.dumps(current, ensure_ascii=False, indent=2).encode("utf-8"),
        use_container_width=True,
    )