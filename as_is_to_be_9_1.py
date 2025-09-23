# as_is_to_be_8.py
import streamlit as st
from bs4 import BeautifulSoup
from typing import Dict, Optional, List, Union

# =====================================================
# Config
# =====================================================
st.set_page_config(page_title="HTML Slide Editor (IRRBB)", layout="wide")
st.title("Process AS_IS-TO_BE HTML slide editor")
st.caption("Upload a template-based HTML slide, edit fields, translate headings & content, and export. Built to handle re-uploads safely.")

# Short instructions button (for brand-new users)
if hasattr(st, "popover"):
    with st.popover("❔ How to use this app"):
        st.markdown(
            """
**In what order to use the app (first-time user guide):**
1. **Upload** your HTML slide in the sidebar (**Upload ▶︎ Upload HTML slide**). The app will parse it and pre-fill the form.
2. **Edit fields** in **Editable fields**. Field labels (e.g., headings like *Ljudje / People / Proces …*) are auto-detected from your uploaded HTML and shown exactly as in the document.
3. **User notes** supports multi‑line input; line breaks are preserved in preview & downloaded HTML (special symbols are allowed).
4. Optionally **Translate** all editable text and section labels via **Translate** (choose target language → **Translate current fields**).
5. Press **✅ Apply changes to preview** to refresh the live **Preview**.
6. If satisfied, click **⬇️ Download updated HTML**.
7. **Utilities → Clear all fields** resets everything (safe for re‑uploads).

> Extra fields present in an uploaded HTML (beyond the standard 5 per side + user notes) are intentionally ignored and excluded from preview & download.
"""
        )
else:
    with st.expander("❔ How to use this app", expanded=False):
        st.markdown(
            """
**In what order to use this app (first-time user guide):**
1. **Upload** your HTML slide in the sidebar (**Upload ▶︎ Upload HTML slide**). The app will parse it and pre-fill the form.
2. **Edit fields** in **Editable fields**. Field labels (e.g., headings like *Ljudje / People / Proces …*) are auto-detected from your uploaded HTML and shown exactly as in the document.
3. **User notes** supports multi‑line input; line breaks are preserved in preview & downloaded HTML (special symbols are allowed).
4. Optionally **Translate** all editable text and section labels via **Translate** (choose target language → **Translate current fields**).
5. Press **✅ Apply changes to preview** to refresh the live **Preview**.
6. If satisfied, click **⬇️ Download updated HTML**.
7. **Utilities → Clear all fields** resets everything (safe for re‑uploads).

> Extra fields present in an uploaded HTML (beyond the standard 5 per side + user notes) are intentionally ignored and excluded from preview & download.
"""
        )

# =====================================================
# Privacy Disclaimer
# =====================================================
st.info("🔒 Privacy Notice: This app does not store or share any data you enter. All inputs remain private within your session and are not saved to any server or file.")

# =====================================================
# Constants & helpers
# =====================================================
FIELD_KEYS = [
    "title",
    "left_label", "right_label",
    "left_people", "left_process", "left_technology", "left_data", "left_output",
    "right_people", "right_process", "right_technology", "right_data", "right_output",
    "user_notes",
]
DEFAULTS: Dict[str, str] = {k: "TBD" for k in FIELD_KEYS}
DEFAULTS.update({
    "left_label": "AS-IS (danes)",
    "right_label": "Ambicija (to-be)",
    "user_notes": "",
})

FALLBACK_HTML = """
# {{title}}
## {{title}}
{{left_label}}
#### People:
{{left_people}}
#### Process:
{{left_process}}
#### Technology:
{{left_technology}}
#### Data:
{{left_data}}
#### Output:
{{left_output}}
{{right_label}}
#### People:
{{right_people}}
#### Process:
{{right_process}}
#### Technology:
{{right_technology}}
#### Data:
{{right_data}}
#### Output:
{{right_output}}
{{user_notes}}
"""

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

# ---------------- Translation ----------------
@st.cache_data(show_spinner=False)
def _get_translator_or_none():
    try:
        from deep_translator import GoogleTranslator
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
        return txt

# ---------------- HTML parsing helpers ----------------
def _text_with_newlines(el) -> str:
    """Extract text preserving line breaks and special symbols."""
    if not el:
        return ""
    txt = el.get_text(separator="\n", strip=False)
    return txt.replace("\r\n", "\n").replace("\r", "\n")

def _headings_from_panel(soup: BeautifulSoup, panel_sel: str) -> List[str]:
    """Return up to first five h3 headings of a panel, preserving punctuation."""
    h3s = soup.select(f"{panel_sel} .section h3")
    out: List[str] = []
    for h in h3s[:5]:
        t = h.get_text(separator=" ", strip=True)
        out.append(t)
    return out

def detect_ui_labels_from_html(html: str) -> Dict[str, Union[List[str], str, None]]:
    """Auto-detect section headings for left/right panels and user notes label; return doc language if available."""
    soup = BeautifulSoup(html, "html.parser")
    left = _headings_from_panel(soup, ".panel.left")
    right = _headings_from_panel(soup, ".panel.right")
    user_h = soup.select_one(".panel.user .section h3")
    user_label = user_h.get_text(separator=" ", strip=True) if user_h else "User notes"
    lang = (soup.html.get("lang") if soup and soup.html else None)
    if lang not in ("sl", "en"):
        lang = None
    return {
        "left": left,
        "right": right,
        "user": user_label,
        "doc_lang": lang,
    }

def parse_html_fields(html: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    def get_text(selector: str) -> str:
        el = soup.select_one(selector)
        return _text_with_newlines(el) if el else ""

    left_sections = soup.select(".panel.left .section p")
    right_sections = soup.select(".panel.right .section p")
    user_section = soup.select_one(".panel.user .section p")

    def sec(idx: int, arr):
        if len(arr) > idx and arr[idx]:
            return _text_with_newlines(arr[idx])
        return ""

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
        "user_notes": _text_with_newlines(user_section) if user_section else "",
    }
    for k in FIELD_KEYS:
        if not fields.get(k):
            fields[k] = DEFAULTS.get(k, "TBD")
    return fields

def apply_fields_to_html(original_html: str, fields: Dict[str, str], label_lang: Optional[str] = None) -> str:
    soup = BeautifulSoup(original_html, "html.parser")

    # Force <html lang="..."> to requested lang if provided
    if label_lang in ("sl", "en") and soup.html is not None:
        soup.html["lang"] = label_lang

    # Helper to set rich text with preserved line breaks as <br/>
    def set_rich_text(el, value: str) -> None:
        if el is None:
            return
        value = (value or "").replace("\r\n", "\n").replace("\r", "\n")
        el.clear()
        parts = value.split("\n")
        for i, part in enumerate(parts):
            el.append(part)  # text node; special symbols preserved/escaped safely
            if i < len(parts) - 1:
                el.append(soup.new_tag("br"))

    # Trim extra sections beyond the standard five per panel (ignore additional fields)
    for panel_sel in (".panel.left", ".panel.right"):
        sections = soup.select(f"{panel_sel} .section")
        if len(sections) > 5:
            for extra in sections[5:]:
                extra.decompose()

    # Keep only the first user section
    user_sections = soup.select(".panel.user .section")
    if len(user_sections) > 1:
        for extra in user_sections[1:]:
            extra.decompose()

    # Set title & side labels
    def set_text(selector: str, value: str) -> None:
        el = soup.select_one(selector)
        if el is not None:
            set_rich_text(el, value)

    set_text("h1", fields["title"])
    set_text(".panel.left .side-label .tag", fields["left_label"])
    set_text(".panel.right .side-label .tag", fields["right_label"])

    # Set panel sections (p elements), preserving line breaks
    def set_sec(panel_sel: str, idx: int, value: str) -> None:
        ps = soup.select(f"{panel_sel} .section p")
        if len(ps) > idx and ps[idx] is not None:
            set_rich_text(ps[idx], value)

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

    # User notes (grey panel) — preserved multi-line
    set_text(".panel.user .section p", fields["user_notes"])

    # Translate static H3 labels if requested
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
                set_rich_text(left_h3s[idx], text)
            if len(right_h3s) > idx and right_h3s[idx]:
                set_rich_text(right_h3s[idx], text)

    # ---- Remove footer so the last visible block is user_notes ----
    # 1) Remove explicit footer tags/known classes/ids
    basic_selectors = [
        "footer",
        "[role='contentinfo']",
        ".footer",
        "#footer",
        ".page-footer",
        ".site-footer",
        ".app-footer",
    ]
    for selector in basic_selectors:
        for el in soup.select(selector):
            el.decompose()

    # 2) Remove any element whose id or class contains 'footer' (case-insensitive)
    #    Avoids reliance on CSS attribute contains selectors (works on older bs4 too)
    for el in list(soup.find_all(True, id=lambda v: isinstance(v, str) and "footer" in v.lower())):
        el.decompose()

    def _class_contains_footer(v):
        if not v:
            return False
        if isinstance(v, str):
            return "footer" in v.lower()
        # v can be list of classes
        return any(isinstance(x, str) and "footer" in x.lower() for x in v)

    for el in list(soup.find_all(True, class_=_class_contains_footer)):
        el.decompose()

    # 3) Ensure user panel is positioned as the last visible content block
    user_panel = soup.select_one(".panel.user")
    if user_panel and user_panel.parent:
        parent = user_panel.parent
        user_panel.extract()
        parent.append(user_panel)

    return str(soup)

def init_fields(fields: Dict[str, str]) -> None:
    for k in FIELD_KEYS:
        st.session_state[k] = fields.get(k, DEFAULTS.get(k, ""))
    st.session_state["fields_obj"] = {k: st.session_state[k] for k in FIELD_KEYS}

def clear_widget_state() -> None:
    for k in list(st.session_state.keys()):
        if k in FIELD_KEYS:
            st.session_state.pop(k)

# =============================== Sidebar ===============================
with st.sidebar:
    st.header("Upload")
    uploaded = st.file_uploader("Upload HTML slide", type=["html", "htm"], accept_multiple_files=False)

    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        new_hash = hash(file_bytes)

        if st.session_state.get("_upload_hash") != new_hash:
            html = file_bytes.decode("utf-8", errors="ignore")
            st.session_state["base_html"] = html

            # Parse values
            parsed = parse_html_fields(html)
            # Detect UI labels (headings) & document language
            ui_detect = detect_ui_labels_from_html(html)

            # Reset and initialize fields
            clear_widget_state()
            init_fields(parsed)

            # Update UI labels in session for dynamic form headers
            st.session_state["_ui_labels"] = {
                "left": ui_detect.get("left") or [],
                "right": ui_detect.get("right") or [],
                "user": ui_detect.get("user") or "User notes",
            }
            # Initialize label language to document's lang if present
            doc_lang = ui_detect.get("doc_lang")
            if doc_lang in ("sl", "en"):
                st.session_state["_label_lang"] = doc_lang

            st.session_state["_upload_hash"] = new_hash
            st.success("Parsed uploaded HTML and refreshed widget values.")

    st.header("Translate")
    lang = st.radio("Translate to", ["sl", "en"], horizontal=True, key="_lang")
    if st.button("🌐 Translate current fields", use_container_width=True):
        src = "sl" if lang == "en" else "en"
        translated = {k: translate_text(st.session_state.get(k, ""), src, lang) for k in FIELD_KEYS}
        init_fields(translated)
        st.session_state["_label_lang"] = lang
        st.toast(f"Translated UI labels + fields to {lang.upper()} (best-effort)")

    st.header("Utilities")
    if st.button("🧹 Clear all fields", use_container_width=True):
        clear_widget_state()
        init_fields({k: "" for k in FIELD_KEYS})
        st.session_state["base_html"] = FALLBACK_HTML
        st.session_state["_upload_hash"] = None
        # Reset UI labels to English defaults for empty state
        st.session_state["_ui_labels"] = {
            "left": [STATIC_LABELS["en"][k] for k in ("people", "process", "technology", "data", "output")],
            "right": [STATIC_LABELS["en"][k] for k in ("people", "process", "technology", "data", "output")],
            "user": "User notes (grey panel)",
        }
        st.toast("Cleared fields and reset base HTML")

# =============================== Main ===============================
base_html = st.session_state.get("base_html", FALLBACK_HTML)
if not any(k in st.session_state for k in FIELD_KEYS):
    init_fields(DEFAULTS.copy())

# Prepare dynamic form labels based on uploaded HTML headings
ui_labels = st.session_state.get("_ui_labels", {})
left_names = ui_labels.get("left") or [STATIC_LABELS["en"][k] for k in ("people", "process", "technology", "data", "output")]
right_names = ui_labels.get("right") or [STATIC_LABELS["en"][k] for k in ("people", "process", "technology", "data", "output")]
user_notes_label = ui_labels.get("user", "User notes (grey panel)")

# Ensure we always have 5 labels per side
def _pad5(lst: List[str], lang_fallback: str = "en") -> List[str]:
    if len(lst) >= 5:
        return lst[:5]
    defaults = [STATIC_LABELS[lang_fallback][k] for k in ("people", "process", "technology", "data", "output")]
    need = 5 - len(lst)
    return lst + defaults[-need:] if need > 0 else lst

label_lang_default = st.session_state.get("_label_lang", "sl")
fallback_lang = label_lang_default if label_lang_default in ("sl", "en") else "en"
left_names = _pad5(left_names, fallback_lang)
right_names = _pad5(right_names, fallback_lang)

with st.form("editor_form", clear_on_submit=False):
    st.subheader("Editable fields")
    st.text_input("Title", key="title")

    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Left label", key="left_label")
        st.text_area(f"Left – {left_names[0]}", key="left_people")
        st.text_area(f"Left – {left_names[1]}", key="left_process")
        st.text_area(f"Left – {left_names[2]}", key="left_technology")
        st.text_area(f"Left – {left_names[3]}", key="left_data")
        st.text_area(f"Left – {left_names[4]}", key="left_output")
    with c2:
        st.text_input("Right label", key="right_label")
        st.text_area(f"Right – {right_names[0]}", key="right_people")
        st.text_area(f"Right – {right_names[1]}", key="right_process")
        st.text_area(f"Right – {right_names[2]}", key="right_technology")
        st.text_area(f"Right – {right_names[3]}", key="right_data")
        st.text_area(f"Right – {right_names[4]}", key="right_output")

    # User notes editor (grey panel) — multi-line preserved
    st.text_area(user_notes_label, key="user_notes")

    submitted = st.form_submit_button("✅ Apply changes to preview", use_container_width=True)

if submitted:
    st.toast("Applied changes")
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