import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

# -----------------------------
# Config
# -----------------------------
APP_NAME = "ClarityCare"
DATA_PATH = Path(__file__).parent / "topics.json"
ASSETS_DIR = Path(__file__).parent / "assets"
IMAGES_DIR = ASSETS_DIR / "images"

CATEGORIES = ["All", "Everyday Symptoms", "Post-Diagnosis Companion"]

BANNED_PHRASES = [
    "you should take",
    "take ",
    "go to the er",
    "don't need a doctor",
    "dont need a doctor",
    "most likely",
    "this means you have",
    "diagnosis:",
    "start taking",
    "stop taking",
    "dose",
    "dosage",
]

st.set_page_config(page_title=APP_NAME, page_icon="🩺", layout="wide")


# -----------------------------
# Styling (aesthetic UI)
# -----------------------------
def inject_css():
    st.markdown(
        """
<style>
/* Layout */
.main .block-container { max-width: 1100px; padding-top: 1.2rem; padding-bottom: 5rem; }

/* Hero */
.hero {
  border: 1px solid rgba(15, 23, 42, .10);
  background: linear-gradient(135deg, rgba(226, 236, 248, .85), rgba(247, 244, 239, .95));
  padding: 28px;
  border-radius: 22px;
  box-shadow: 0 18px 50px -35px rgba(0,0,0,.35);
}
.hero h1 { margin: 0; font-size: 2.0rem; }
.hero p { margin: .35rem 0 0 0; color: rgba(15, 23, 42, .75); font-size: 1.05rem; }
.badge {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(15,23,42,.15);
  background: white;
  font-size: .85rem;
  font-weight: 700;
  letter-spacing: .02em;
}

/* Cards */
.card {
  border: 1px solid rgba(15, 23, 42, .10);
  background: white;
  border-radius: 18px;
  padding: 16px 16px 12px 16px;
  box-shadow: 0 18px 45px -40px rgba(0,0,0,.40);
}
.card-title { font-size: 1.05rem; font-weight: 800; margin: 0; }
.card-meta { color: rgba(15,23,42,.60); font-size: .9rem; margin-top: 4px; }
.pill {
  display:inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(15,23,42,.12);
  background: rgba(232, 222, 209, .55);
  font-size: .78rem;
  font-weight: 700;
}

/* Safety bar */
.safety-top {
  position: sticky;
  top: 0;
  z-index: 99;
  padding: 10px 14px;
  border-radius: 14px;
  background: rgba(11, 15, 26, 1);
  color: rgba(247, 244, 239, 1);
  border: 1px solid rgba(247,244,239,.18);
  margin-bottom: 14px;
  font-size: .95rem;
}

/* Footer */
.footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(11, 15, 26, 1);
  color: rgba(247, 244, 239, 1);
  border-top: 1px solid rgba(247,244,239,.18);
  padding: 10px 18px;
  font-size: .92rem;
}
.footer a { color: rgba(226, 236, 248, 1); text-decoration: underline; }

/* Streamlit tweaks */
div[data-testid="stExpander"] > details {
  border-radius: 16px !important;
  border: 1px solid rgba(15,23,42,.10) !important;
  background: white !important;
  box-shadow: 0 18px 45px -40px rgba(0,0,0,.40) !important;
}
div[data-testid="stExpander"] summary {
  font-weight: 800 !important;
  padding: 12px 14px !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# Utilities
# -----------------------------
def load_topics() -> List[Dict[str, Any]]:
    if not DATA_PATH.exists():
        st.error(f"Missing topics.json at: {DATA_PATH}")
        st.stop()
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def matches_search(topic: Dict[str, Any], q: str) -> bool:
    if not q:
        return True
    qn = normalize_text(q)
    hay = " ".join(
        [
            topic.get("title", ""),
            topic.get("oneMinuteSummary", ""),
            topic.get("eli5Summary", ""),
        ]
    )
    return qn in normalize_text(hay)


def safety_scan_topic(topic: Dict[str, Any]) -> List[str]:
    """Developer-only warnings. Does not block."""
    warnings = []
    # Collect all strings in the topic
    def collect(v: Any) -> List[str]:
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            out = []
            for item in v:
                out.extend(collect(item))
            return out
        if isinstance(v, dict):
            out = []
            for vv in v.values():
                out.extend(collect(vv))
            return out
        return []

    strings = collect(topic)
    for s in strings:
        low = s.lower()
        for phrase in BANNED_PHRASES:
            if phrase in low:
                warnings.append(f'Banned phrase "{phrase}" found in: {s[:140]}...')
                break

        # Long sentence heuristic
        for sent in re.split(r"[.!?]", s):
            sent = sent.strip()
            if not sent:
                continue
            wc = len(sent.split())
            if wc > 25:
                warnings.append(f"Long sentence ({wc} words): {sent[:140]}...")
                break

    return warnings


def render_image(src: str, alt: Optional[str] = None):
    # src in JSON is like "/images/bp-diagram.svg"
    # We map it to assets/images/bp-diagram.svg
    fname = src.replace("/images/", "").lstrip("/")
    path = IMAGES_DIR / fname
    if path.exists():
        st.image(str(path), caption=alt or "", use_container_width=True)
    else:
        st.info(f"(Visual missing) Add file: {path}")


def render_video(embed_url: str):
    # Streamlit can embed via iframe (st.components)
    # but simplest: st.video supports YouTube URLs directly.
    st.video(embed_url)


# -----------------------------
# App UI
# -----------------------------
inject_css()

# Safety banner (top)
st.markdown(
    """
<div class="safety-top">
  <strong>Education only.</strong> Not medical advice. This tool does not diagnose, assess urgency, or provide treatment instructions.
</div>
""",
    unsafe_allow_html=True,
)

topics = load_topics()

# Sidebar controls
with st.sidebar:
    st.markdown(f"## {APP_NAME}")
    st.caption("Simple health education in under a minute — with clear boundaries.")

    category = st.selectbox("Category", CATEGORIES, index=0)

    q = st.text_input("Search topics", placeholder="Try headache, asthma, heartburn…")

    st.markdown("---")
    st.markdown("### Reading style")
    eli5_mode = st.toggle("Show ELI5 summaries", value=True)
    extra_detail = st.toggle("Show extra detail (if available)", value=False)

    st.markdown("---")
    dev_mode = st.toggle("Developer safety warnings", value=False)
    st.caption("Shows console-like warnings for banned phrases & long sentences.")

# Hero / UVP
st.markdown(
    f"""
<div class="hero">
  <span class="badge">Education only</span>
  <h1>{APP_NAME}</h1>
  <p><strong>Understand a diagnosis or symptom in under a minute</strong> — with simple language, analogies, visuals, and clinician-visit question prompts.</p>
  <div style="margin-top: 14px; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
    <div class="card"><p class="card-title">Fast</p><p class="card-meta">Designed to read in ~60 seconds per topic.</p></div>
    <div class="card"><p class="card-title">Safe</p><p class="card-meta">No diagnosis, no urgency advice, no medication instructions.</p></div>
    <div class="card"><p class="card-title">Clear</p><p class="card-meta">“What’s happening in your body” with simple analogies.</p></div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.write("")

# Filter topics
filtered = []
for t in topics:
    if category != "All" and t.get("category") != category:
        continue
    if not matches_search(t, q):
        continue
    filtered.append(t)

# Results header
left, right = st.columns([0.7, 0.3])
with left:
    st.subheader("Explore topics")
    st.caption("Tap a topic to expand. Keep language simple and educational.")
with right:
    st.markdown(
        f"""
<div style="text-align:right;">
  <span class="pill">{len(filtered)} topics</span>
</div>
""",
        unsafe_allow_html=True,
    )

if not filtered:
    st.info("No topics match your search. Try a shorter keyword.")
    st.stop()

# Render topics in a responsive grid
# Streamlit doesn't have native cards grid, so we use columns in rows of 2.
cols_per_row = 2
for i in range(0, len(filtered), cols_per_row):
    row = st.columns(cols_per_row)
    for j in range(cols_per_row):
        idx = i + j
        if idx >= len(filtered):
            break

        t = filtered[idx]
        title = t.get("title", "Untitled")
        cat = t.get("category", "")
        summary = t.get("oneMinuteSummary", "")

        with row[j]:
            # Card header
            st.markdown(
                f"""
<div class="card">
  <p class="card-title">{title}</p>
  <p class="card-meta">{summary}</p>
  <div style="margin-top: 10px;">
    <span class="pill">{cat}</span>
    <span class="pill">~60 seconds</span>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

            # Expander for full content
            with st.expander("Open", expanded=False):
                if dev_mode:
                    warns = safety_scan_topic(t)
                    if warns:
                        st.warning("Safety/style warnings detected (dev only):")
                        for w in warns[:8]:
                            st.caption(f"- {w}")
                    else:
                        st.success("No safety/style warnings detected.")

                st.markdown("### One-Minute Summary")
                st.write(t.get("oneMinuteSummary", ""))

                if extra_detail and t.get("extraDetail", {}).get("oneMinuteSummary"):
                    st.caption(t["extraDetail"]["oneMinuteSummary"])

                if eli5_mode:
                    st.markdown("### ELI5 Summary")
                    st.write(t.get("eli5Summary", ""))

                st.markdown("### What’s happening in your body")
                for item in t.get("whatsHappening", []):
                    st.markdown(f"- {item}")
                if extra_detail and t.get("extraDetail", {}).get("whatsHappening"):
                    st.caption(t["extraDetail"]["whatsHappening"])

                st.markdown("### Analogy")
                analogy = t.get("analogy", {})
                if analogy:
                    st.write(f"**{analogy.get('title','')}**")
                    st.write(analogy.get("story", ""))
                    if extra_detail and t.get("extraDetail", {}).get("analogy"):
                        st.caption(t["extraDetail"]["analogy"])

                st.markdown("### People often notice")
                for item in t.get("peopleOftenNotice", []):
                    st.markdown(f"- {item}")
                if extra_detail and t.get("extraDetail", {}).get("peopleOftenNotice"):
                    st.caption(t["extraDetail"]["peopleOftenNotice"])

                st.markdown("### General self-care education")
                st.caption("Non-prescriptive, no meds, no urgency guidance.")
                for item in t.get("generalSelfCare", []):
                    st.markdown(f"- {item}")
                if extra_detail and t.get("extraDetail", {}).get("generalSelfCare"):
                    st.caption(t["extraDetail"]["generalSelfCare"])

                if t.get("category") == "Post-Diagnosis Companion" and t.get("questionsForClinician"):
                    st.markdown("### Questions for your clinician")
                    for item in t.get("questionsForClinician", []):
                        st.markdown(f"- {item}")
                    if extra_detail and t.get("extraDetail", {}).get("questionsForClinician"):
                        st.caption(t["extraDetail"]["questionsForClinician"])

                st.markdown("### Visual")
                visuals = t.get("visuals", [])
                if visuals:
                    render_image(visuals[0].get("src", ""), visuals[0].get("alt"))
                else:
                    st.info("No visual added yet for this topic.")

                videos = t.get("videos", [])
                if videos:
                    st.markdown("### Video (optional)")
                    st.caption("Educational resource.")
                    # Streamlit video works with full YouTube URLs (not /embed/ only)
                    # If you stored an embed URL, it still usually works; if not, swap to a normal youtube link.
                    render_video(videos[0].get("embedUrl", ""))

                st.markdown("### Resources")
                resources = t.get("resources", [])
                if resources:
                    for r in resources:
                        label = r.get("label", "Resource")
                        url = r.get("url", "")
                        st.markdown(f"- [{label}]({url})")
                else:
                    st.info("No resources yet.")

                st.caption(f"Last reviewed: {t.get('lastReviewed', '—')}")

# Fixed footer
st.markdown(
    """
<div class="footer">
  <strong>Education only —</strong> not diagnosis, not urgency guidance, not treatment instructions.
  <span style="opacity:.85">If you’re worried about a symptom, use professional care and bring questions to a clinician.</span>
</div>
""",
    unsafe_allow_html=True,
)

