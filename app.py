"""
Big-O Complexity Analyzer — Developer Dashboard UI
Features: Single Analysis, Side-by-Side Comparison, Batch File Analysis,
          Streaming Output, Multiple Model Support, Complexity Visualization,
          Analysis History, Confidence Score, Export Results, Syntax Highlighting.
"""

import time
import json
from datetime import datetime
import streamlit as st

from analyzer import analyze_complexity, analyze_complexity_stream, analyze_file_functions, unload_model
from extractor import extract_functions
from config import BACKEND, OLLAMA_MODELS, GEMINI_MODEL, MODEL_META
from visualizer import build_complexity_chart
from exporter import to_markdown, to_pdf

try:
    from code_editor import code_editor
    _HAS_CODE_EDITOR = True
except ImportError:
    _HAS_CODE_EDITOR = False

# ─── Session State ───────────────────────────────────────────────────────────────────
for _key, _val in {
    "model_busy": False,
    "busy_model_name": "",
    "busy_task": "",
    "history": [],          # list of past analysis results
    "last_result": None,    # most recent result (for export)
    "last_code": "",        # most recent code snippet (for export)
}.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Big-O Complexity Analyzer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ── Global ── */
    .stApp { font-family: 'Inter', -apple-system, sans-serif; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ── Hero Bar ── */
    .hero-bar {
        display: flex; align-items: center; gap: 0.75rem;
        padding: 0.5rem 0 0.25rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        margin-bottom: 1.25rem;
    }
    .hero-bar .logo { font-size: 1.5rem; }
    .hero-bar h1 {
        font-size: 1.4rem; font-weight: 700; color: #00ADB5;
        margin: 0; letter-spacing: -0.01em;
    }
    .hero-bar .tag {
        font-size: 0.65rem; font-weight: 600;
        padding: 0.15rem 0.5rem; border-radius: 4px;
        background: rgba(0,173,181,0.12); color: #00ADB5;
        text-transform: uppercase; letter-spacing: 0.08em;
    }

    /* ── Section Headers ── */
    .section-header {
        font-size: 0.7rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.12em;
        color: rgba(226,232,240,0.4);
        margin: 1.5rem 0 0.75rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }

    /* ── Metric Panels ── */
    .metric-panel {
        background: #1E293B;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px; padding: 1.25rem; margin-bottom: 0.75rem;
        transition: border-color 0.2s ease;
    }
    .metric-panel:hover { border-color: rgba(0,173,181,0.2); }
    .metric-label {
        font-size: 0.65rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.1em;
        color: rgba(226,232,240,0.4); margin-bottom: 0.4rem;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.5rem; font-weight: 700; color: #00ADB5;
    }
    .metric-value-sm {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.1rem; font-weight: 600; color: #E2E8F0;
    }

    /* ── Info Rows ── */
    .info-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.6rem 0; border-bottom: 1px solid rgba(255,255,255,0.03);
    }
    .info-row:last-child { border-bottom: none; }
    .info-key { font-size: 0.8rem; font-weight: 500; color: rgba(226,232,240,0.5); }
    .info-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem; font-weight: 600; color: #E2E8F0;
    }

    /* ── Reasoning Box ── */
    .reasoning-box {
        background: #1E293B;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px; padding: 1.25rem;
        line-height: 1.75; font-size: 0.9rem;
        color: rgba(226,232,240,0.85);
    }

    /* ── Streaming Token Box ── */
    .stream-box {
        background: #0F172A;
        border: 1px solid rgba(0,173,181,0.2);
        border-radius: 10px; padding: 1.25rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem; line-height: 1.75;
        color: rgba(226,232,240,0.85);
        min-height: 120px;
        white-space: pre-wrap;
        word-break: break-word;
    }

    /* ── Optimization Panel ── */
    .opt-panel {
        background: #1E293B;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px; padding: 1.25rem;
    }
    .opt-badge-yes {
        display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px;
        font-size: 0.7rem; font-weight: 700;
        background: rgba(34,197,94,0.12); color: #22c55e; letter-spacing: 0.05em;
    }
    .opt-badge-no {
        display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px;
        font-size: 0.7rem; font-weight: 700;
        background: rgba(100,116,139,0.15); color: #94a3b8; letter-spacing: 0.05em;
    }

    /* ── Status Badges ── */
    .status-badge {
        display: inline-block; padding: 0.25rem 0.75rem; border-radius: 4px;
        font-size: 0.7rem; font-weight: 700; letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .status-success {
        background: rgba(0,173,181,0.1); color: #00ADB5;
        border: 1px solid rgba(0,173,181,0.2);
    }
    .status-error {
        background: rgba(239,68,68,0.1); color: #ef4444;
        border: 1px solid rgba(239,68,68,0.2);
    }

    /* ── Complexity Grid ── */
    .complexity-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }

    /* ── Compare Winner Banner ── */
    .winner-banner {
        padding: 0.75rem 1.25rem; border-radius: 10px;
        font-size: 0.9rem; font-weight: 600;
        text-align: center; margin: 0.75rem 0;
    }
    .winner-a {
        background: linear-gradient(135deg, rgba(0,173,181,0.15), rgba(0,173,181,0.05));
        border: 1px solid rgba(0,173,181,0.3); color: #00ADB5;
    }
    .winner-b {
        background: linear-gradient(135deg, rgba(168,85,247,0.15), rgba(168,85,247,0.05));
        border: 1px solid rgba(168,85,247,0.3); color: #a855f7;
    }
    .winner-tie {
        background: linear-gradient(135deg, rgba(251,191,36,0.12), rgba(251,191,36,0.04));
        border: 1px solid rgba(251,191,36,0.25); color: #fbbf24;
    }

    /* ── Compare Side Header ── */
    .compare-header-a {
        font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.1em; color: #00ADB5; margin-bottom: 0.5rem;
    }
    .compare-header-b {
        font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.1em; color: #a855f7; margin-bottom: 0.5rem;
    }
    .metric-value-a {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.5rem; font-weight: 700; color: #00ADB5;
    }
    .metric-value-b {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.5rem; font-weight: 700; color: #a855f7;
    }

    /* ── Model Chip ── */
    .model-chip {
        display: inline-block; padding: 0.15rem 0.55rem;
        border-radius: 4px; font-size: 0.65rem; font-weight: 600;
        background: rgba(0,173,181,0.08); color: #00ADB5;
        border: 1px solid rgba(0,173,181,0.15);
        font-family: 'JetBrains Mono', monospace;
    }

    /* ── Batch Table ── */
    .batch-table-wrap {
        background: #1E293B;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px; overflow: hidden;
    }
    .batch-table {
        width: 100%; border-collapse: collapse;
        font-size: 0.82rem;
    }
    .batch-table thead tr {
        background: rgba(0,173,181,0.08);
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .batch-table th {
        padding: 0.75rem 1rem; text-align: left;
        font-size: 0.65rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.1em;
        color: rgba(226,232,240,0.5);
    }
    .batch-table td {
        padding: 0.65rem 1rem;
        border-bottom: 1px solid rgba(255,255,255,0.03);
        color: rgba(226,232,240,0.85);
    }
    .batch-table tr:last-child td { border-bottom: none; }
    .batch-table tr:hover td { background: rgba(255,255,255,0.02); }
    .batch-fn-name {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600; color: #E2E8F0;
    }
    .batch-complexity {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700; color: #00ADB5;
    }
    .batch-opt-yes { color: #22c55e; font-weight: 600; }
    .batch-opt-no  { color: #64748b; font-weight: 600; }

    /* ── Confidence Bar ── */
    .conf-wrap {
        margin: 0.75rem 0 0.25rem 0;
    }
    .conf-label {
        font-size: 0.65rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.1em;
        color: rgba(226,232,240,0.4); margin-bottom: 0.4rem;
    }
    .conf-bar-bg {
        background: rgba(255,255,255,0.05);
        border-radius: 999px; height: 8px; overflow: hidden;
    }
    .conf-bar-fill {
        height: 100%; border-radius: 999px;
        transition: width 0.6s cubic-bezier(.4,0,.2,1);
    }
    .conf-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem; font-weight: 700;
        margin-top: 0.3rem;
    }

    /* ── History Card ── */
    .hist-card {
        background: #1E293B;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px; padding: 1rem 1.25rem;
        margin-bottom: 0.6rem;
        transition: border-color 0.2s;
    }
    .hist-card:hover { border-color: rgba(0,173,181,0.2); }
    .hist-meta {
        font-size: 0.7rem; color: rgba(226,232,240,0.35);
        font-family: 'JetBrains Mono', monospace;
        margin-bottom: 0.4rem;
    }
    .hist-cx {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.2rem; font-weight: 700; color: #00ADB5;
        display: inline-block; margin-right: 0.75rem;
    }
    .hist-space {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem; color: rgba(226,232,240,0.55);
    }

    /* ── Export buttons row ── */
    .export-row {
        display: flex; gap: 0.5rem; margin-top: 0.75rem;
    }

    /* ── Code editor wrapper ── */
    .code-editor-wrap iframe {
        border-radius: 8px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
    }
    .stTextArea textarea {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.85rem !important; border-radius: 8px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        background: #0F172A !important; color: #E2E8F0 !important;
        padding: 1rem !important; line-height: 1.6 !important;
    }
    .stTextArea textarea:focus {
        border-color: rgba(0,173,181,0.4) !important;
        box-shadow: 0 0 0 2px rgba(0,173,181,0.08) !important;
    }
    .stTextArea textarea::placeholder { color: rgba(226,232,240,0.25) !important; }

    /* ── Buttons ── */
    .stButton > button {
        border-radius: 8px !important; padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important; font-size: 0.85rem !important;
        border: 1px solid #00ADB5 !important;
        background: rgba(0,173,181,0.1) !important;
        color: #00ADB5 !important; transition: all 0.2s ease !important;
        letter-spacing: 0.02em !important;
    }
    .stButton > button:hover {
        background: rgba(0,173,181,0.2) !important;
        box-shadow: 0 0 15px rgba(0,173,181,0.1) !important;
    }
    .stButton > button:active { background: rgba(0,173,181,0.3) !important; }

    /* ── Selectbox ── */
    .stSelectbox > div > div {
        border-radius: 8px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        background: #0F172A !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background: #0F172A;
        border-radius: 10px;
        padding: 4px;
        border: 1px solid rgba(255,255,255,0.06);
        margin-bottom: 1.25rem;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        padding: 0.5rem 1.25rem !important;
        color: rgba(226,232,240,0.5) !important;
        border: none !important;
        transition: all 0.2s !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(0,173,181,0.12) !important;
        color: #00ADB5 !important;
    }

    /* ── Progress bar ── */
    .stProgress > div > div {
        background: linear-gradient(90deg, #00ADB5, #00d4df) !important;
        transition: width 0.3s ease !important;
    }
    .stProgress > div {
        background: rgba(0,173,181,0.08) !important;
        border-radius: 999px !important;
        height: 6px !important;
    }

    /* ── Lock Banner ── */
    .lock-banner {
        display: flex; align-items: center; gap: 0.75rem;
        padding: 0.75rem 1.25rem; border-radius: 10px;
        background: linear-gradient(135deg, rgba(251,191,36,0.08), rgba(251,191,36,0.03));
        border: 1px solid rgba(251,191,36,0.25);
        margin-bottom: 1rem;
    }
    .lock-dot {
        width: 8px; height: 8px; border-radius: 50%;
        background: #fbbf24;
        animation: pulse-dot 1.2s ease-in-out infinite;
        flex-shrink: 0;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.7); }
    }
    .lock-text {
        font-size: 0.82rem; font-weight: 600; color: #fbbf24;
    }
    .lock-model {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem; color: rgba(251,191,36,0.7);
    }

    /* ── Disabled button override ── */
    .stButton > button:disabled {
        opacity: 0.35 !important;
        cursor: not-allowed !important;
        border-color: rgba(255,255,255,0.1) !important;
        color: rgba(226,232,240,0.3) !important;
    }

    /* ── Upload area ── */
    .stFileUploader > div {
        border: 1px dashed rgba(0,173,181,0.3) !important;
        border-radius: 10px !important;
        background: rgba(0,173,181,0.04) !important;
    }

    /* ── Separator ── */
    .sep { height: 1px; background: rgba(255,255,255,0.04); margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

COMPLEXITY_ORDER = [
    "O(1)", "O(log n)", "O(log N)",
    "O(n)", "O(N)", "O(n log n)", "O(N log N)",
    "O(n^2)", "O(N^2)", "O(n^3)", "O(N^3)",
    "O(2^n)", "O(2^N)", "O(n!)", "O(N!)",
]

def _complexity_rank(cx: str) -> int:
    cx_clean = cx.strip()
    for i, c in enumerate(COMPLEXITY_ORDER):
        if c.lower() == cx_clean.lower():
            return i
    return 999  # unknown — treat as high

def _confidence_bar(confidence: float):
    """Render a styled confidence progress bar with color coding."""
    pct = int(confidence * 100)
    if confidence >= 0.75:
        color = "#22c55e"    # green
        label_color = "#22c55e"
    elif confidence >= 0.45:
        color = "#fbbf24"    # amber
        label_color = "#fbbf24"
    else:
        color = "#ef4444"    # red
        label_color = "#ef4444"

    st.markdown(f"""
    <div class="conf-wrap">
        <div class="conf-label">Analysis Confidence</div>
        <div class="conf-bar-bg">
            <div class="conf-bar-fill"
                 style="width:{pct}%; background:{color};"></div>
        </div>
        <div class="conf-val" style="color:{label_color}">{pct}%</div>
    </div>
    """, unsafe_allow_html=True)


def _render_export_buttons(result: dict, code_snippet: str = "", key_prefix: str = "main"):
    """Render Markdown + PDF download buttons for a result."""
    try:
        md_bytes = to_markdown(result, code_snippet).encode("utf-8")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        col_md, col_pdf, _ = st.columns([1, 1, 4])
        with col_md:
            st.download_button(
                "⬇\ufe0f Markdown",
                data=md_bytes,
                file_name=f"bigo_report_{ts}.md",
                mime="text/markdown",
                key=f"dl_md_{key_prefix}",
                use_container_width=True,
            )
        with col_pdf:
            pdf_bytes = to_pdf(result, code_snippet)
            st.download_button(
                "⬇\ufe0f PDF",
                data=pdf_bytes,
                file_name=f"bigo_report_{ts}.pdf",
                mime="application/pdf",
                key=f"dl_pdf_{key_prefix}",
                use_container_width=True,
            )
    except Exception as e:
        st.caption(f"Export error: {e}")


def _record_history(result: dict, code_snippet: str, model: str):
    """Prepend an entry to the analysis history in session state."""
    entry = {
        "timestamp": datetime.now().strftime("%H:%M:%S · %d %b %Y"),
        "model": model or "—",
        "language": result.get("language", "Unknown"),
        "time_complexity": result.get("time_complexity", "?"),
        "space_complexity": result.get("space_complexity", "?"),
        "confidence": result.get("confidence", 0.5),
        "code_snippet": code_snippet[:200],
        "result": result,
    }
    st.session_state.history.insert(0, entry)
    # Cap history at 50 entries
    st.session_state.history = st.session_state.history[:50]


def _render_result_panel(result: dict, side_prefix: str = "", color: str = "#00ADB5"):
    """Render the standard complexity result cards."""
    time_cx = result.get("time_complexity", "N/A")
    space_cx = result.get("space_complexity", "N/A")
    best = result.get("best_case", "N/A")
    worst = result.get("worst_case", "N/A")
    reason = result.get("reasoning", "")
    better = result.get("better_possible", "N/A")
    sug_algo = result.get("suggested_algorithm", "N/A")
    exp_cx = result.get("expected_complexity", "N/A")
    opt_reason = result.get("optimization_reason", "N/A")
    model_used = result.get("model_used", "—")

    value_cls = "metric-value-a" if color == "#00ADB5" else "metric-value-b"

    st.markdown(f"""
    <div class="complexity-grid">
        <div class="metric-panel">
            <div class="metric-label">⏱ Time Complexity</div>
            <div class="{value_cls}">{time_cx}</div>
        </div>
        <div class="metric-panel">
            <div class="metric-label">💾 Space Complexity</div>
            <div class="{value_cls}">{space_cx}</div>
        </div>
        <div class="metric-panel">
            <div class="metric-label">🟢 Best Case</div>
            <div class="metric-value-sm">{best}</div>
        </div>
        <div class="metric-panel">
            <div class="metric-label">🔴 Worst Case</div>
            <div class="metric-value-sm">{worst}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Explanation</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="reasoning-box">{reason}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Optimization Suggestion</div>', unsafe_allow_html=True)
    badge_class = "opt-badge-yes" if str(better).upper() == "YES" else "opt-badge-no"
    badge_text = "YES — Optimization Available" if str(better).upper() == "YES" else "NO — Already Optimal"
    st.markdown(f"""
    <div class="opt-panel">
        <div class="info-row">
            <span class="info-key">Better Complexity Possible?</span>
            <span class="{badge_class}">{badge_text}</span>
        </div>
        <div class="info-row">
            <span class="info-key">Suggested Algorithm</span>
            <span class="info-val">{sug_algo}</span>
        </div>
        <div class="info-row">
            <span class="info-key">Expected Complexity</span>
            <span class="info-val">{exp_cx}</span>
        </div>
        <div class="info-row">
            <span class="info-key">Reason</span>
            <span class="info-val" style="max-width:65%;text-align:right;">{opt_reason}</span>
        </div>
        <div class="info-row">
            <span class="info-key">Model</span>
            <span class="model-chip">{model_used}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Confidence bar
    confidence = result.get("confidence", None)
    if confidence is not None:
        _confidence_bar(float(confidence))


# ═══════════════════════════════════════════════════════════════════════════════
# Header
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="hero-bar">
    <span class="logo">⚡</span>
    <h1>Big-O Complexity Analyzer</h1>
    <span class="tag">Local LLM</span>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Global Controls (Model + Language)
# ═══════════════════════════════════════════════════════════════════════════════

LANGUAGES = ["Auto Detect", "Python", "C++", "Java", "JavaScript",
             "Go", "Rust", "C", "TypeScript"]

if BACKEND == "ollama":
    # Build labelled options: "qwen2.5-coder:7b  7B · Code  ⚡⚡⚡"
    def _model_label(m: str) -> str:
        meta = MODEL_META.get(m)
        if meta:
            return f"{m}  ·  {meta[0]}  {meta[1]}"
        return m

    _model_options = OLLAMA_MODELS
    _model_labels  = [_model_label(m) for m in _model_options]

    ctrl_model, ctrl_lang, ctrl_stream = st.columns([2, 2, 1])
    with ctrl_model:
        _sel_idx = st.selectbox(
            "Model",
            range(len(_model_options)),
            format_func=lambda i: _model_labels[i],
            help="⚡⚡⚡ = fast (small), ⚡ = slow (thinking/large)",
            disabled=st.session_state.model_busy,
        )
        selected_model = _model_options[_sel_idx]

        # Warn if user picks a slow thinking model
        _speed = MODEL_META.get(selected_model, ("?", "⚡⚡"))[1]
        if _speed == "⚡":
            st.caption("⚠️ This is a large/thinking model — expect slow responses. Try `qwen2.5-coder:7b` or `gemma3:4b` for speed.")
    with ctrl_lang:
        selected_language = st.selectbox("Language", LANGUAGES, label_visibility="visible",
                                         disabled=st.session_state.model_busy)
    with ctrl_stream:
        use_streaming = st.toggle("⚡ Stream", value=True, help="Show tokens as they arrive",
                                  disabled=st.session_state.model_busy)
else:
    ctrl_lang, = st.columns([1])
    with ctrl_lang:
        selected_language = st.selectbox("Language", LANGUAGES)
    selected_model = None
    use_streaming = False

# ── Global lock banner ───────────────────────────────────────────────────────
if st.session_state.model_busy:
    lock_col, reset_col = st.columns([6, 1])
    with lock_col:
        st.markdown(f"""
        <div class="lock-banner">
            <div class="lock-dot"></div>
            <div>
                <div class="lock-text">🔒 Model Busy — {st.session_state.busy_task}</div>
                <div class="lock-model">{st.session_state.busy_model_name}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with reset_col:
        if st.button("↺ Reset", key="reset_lock", help="Force-clear the model lock if it got stuck"):
            st.session_state.model_busy = False
            st.session_state.busy_model_name = ""
            st.session_state.busy_task = ""
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# Tabs
# ═══════════════════════════════════════════════════════════════════════════════

tab_single, tab_compare, tab_batch, tab_history = st.tabs([
    "🔍  Single Analysis",
    "⚖️  Side-by-Side Compare",
    "📂  Batch File Analysis",
    "📜  History",
])


# ███████████████████████████████████████████████████████████████████████████████
#  TAB 1 — SINGLE ANALYSIS  (with streaming support)
# ███████████████████████████████████████████████████████████████████████████████

with tab_single:
    # ── Code Input — textarea (reliable) + live syntax-highlighted preview ─
    code_input = st.text_area(
        "Code Input",
        height=320,
        placeholder="// Paste your function or algorithm here...\n\ndef my_function(arr):\n    for i in range(len(arr)):\n        for j in range(len(arr)):\n            ...",
        label_visibility="collapsed",
        key="single_code",
    )

    # Live syntax-highlighted preview (collapsible, auto-detects language)
    if code_input and code_input.strip():
        _lang_preview = selected_language.lower() if selected_language != "Auto Detect" else "python"
        with st.expander("🎨 Syntax Preview", expanded=False):
            st.code(code_input, language=_lang_preview, line_numbers=True)

    analyze_clicked = st.button(
        "▶  Analyze",
        use_container_width=False,
        key="single_analyze",
        disabled=st.session_state.model_busy,
    )

    if analyze_clicked:
        if not code_input or not code_input.strip():
            st.warning("⚠  Paste some code before analyzing.")
        else:
            # ── STREAMING PATH ──────────────────────────────────────────────
            if use_streaming and BACKEND == "ollama":
                st.markdown('<div class="section-header">Live Reasoning Stream</div>',
                            unsafe_allow_html=True)
                stream_placeholder = st.empty()
                progress_placeholder = st.empty()

                streamed_text = ""
                final_raw = ""
                start_time = time.time()
                token_count = 0

                # Acquire lock
                st.session_state.model_busy = True
                st.session_state.busy_model_name = selected_model or "unknown"
                st.session_state.busy_task = "Single Analysis · Streaming"

                try:
                    gen = analyze_complexity_stream(code_input, selected_language, selected_model)

                    for token in gen:
                        if token.startswith("__RESULT__"):
                            final_raw = token[len("__RESULT__"):]
                            break
                        streamed_text += token
                        token_count += 1

                        # Animated indeterminate progress (oscillates 0→90%)
                        progress_val = min(0.9, (token_count % 120) / 120)
                        progress_placeholder.progress(
                            progress_val,
                            text=f"⚙ Generating · {token_count} tokens · {round(time.time()-start_time,1)}s",
                        )
                        stream_placeholder.markdown(
                            f'<div class="stream-box">{streamed_text}</div>',
                            unsafe_allow_html=True,
                        )
                finally:
                    # Always release lock
                    st.session_state.model_busy = False
                    if unload_model(selected_model or ""):
                        st.session_state._just_unloaded = True

                progress_placeholder.progress(1.0, text="✓ Generation complete")
                time.sleep(0.4)
                progress_placeholder.empty()

                elapsed = round(time.time() - start_time, 2)

                # Parse the collected output
                from parser import parse_output
                result = parse_output(final_raw)
                result["model_used"] = selected_model or "unknown"

                if result["success"]:
                    stream_placeholder.empty()  # hide raw stream, show structured results
                    st.markdown(
                        f'<span class="status-badge status-success">✓ Analysis Complete · {elapsed}s · {token_count} tokens</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown('<div class="section-header">Analysis Metrics</div>',
                                unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="metric-panel">
                        <div class="info-row">
                            <span class="info-key">Analysis Time</span>
                            <span class="info-val">{elapsed}s</span>
                        </div>
                        <div class="info-row">
                            <span class="info-key">Tokens Generated</span>
                            <span class="info-val">{token_count}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-key">Detected Language</span>
                            <span class="info-val">{result['language']}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-key">Model</span>
                            <span class="model-chip">{result['model_used']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown('<div class="section-header">Complexity Results</div>',
                                unsafe_allow_html=True)
                    _render_result_panel(result)

                    # ── Complexity Visualization ──
                    st.markdown('<div class="section-header">Growth Curve Visualization</div>',
                                unsafe_allow_html=True)
                    try:
                        fig = build_complexity_chart(result["time_complexity"])
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as _ve:
                        st.caption(f"Chart error: {_ve}")

                    # ── Export ──
                    st.markdown('<div class="section-header">Export Report</div>',
                                unsafe_allow_html=True)
                    _render_export_buttons(result, code_input, key_prefix="stream")

                    # ── Record history ──
                    _record_history(result, code_input, selected_model or "")

                else:
                    # Streaming got something but couldn't parse — show raw
                    st.markdown(
                        '<span class="status-badge status-error">⚠ Partial Result — Model did not return valid JSON</span>',
                        unsafe_allow_html=True,
                    )
                    st.info(
                        "💡 **Tip:** Some models (e.g. `codellama`) ignore JSON-only instructions and write prose instead. "
                        "Try switching to **`qwen2.5-coder:7b`** or **`mistral`** for reliable structured output.",
                    )
                    st.markdown('<div class="section-header">Raw LLM Output</div>',
                                unsafe_allow_html=True)
                    stream_placeholder.markdown(
                        f'<div class="stream-box">{streamed_text}</div>',
                        unsafe_allow_html=True,
                    )

                if getattr(st.session_state, "_just_unloaded", False):
                    st.caption("🔌 GPU memory freed — model unloaded from VRAM")
                    st.session_state._just_unloaded = False

            # ── BLOCKING PATH ───────────────────────────────────────────────
            else:
                st.session_state.model_busy = True
                st.session_state.busy_model_name = selected_model or "unknown"
                st.session_state.busy_task = "Single Analysis"
                progress_bar = st.progress(0, text="Starting analysis...")
                try:
                    start_time = time.time()
                    # Fake progress animation while blocking
                    import threading
                    _done = [False]
                    _result_holder = [None]

                    def _run():
                        _result_holder[0] = analyze_complexity(
                            code_input, selected_language, selected_model
                        )
                        _done[0] = True

                    t = threading.Thread(target=_run, daemon=True)
                    t.start()
                    step = 0
                    while not _done[0]:
                        step = (step + 3) % 88
                        progress_bar.progress(
                            (step + 5) / 100,
                            text=f"⚙ Analyzing · {round(time.time()-start_time,1)}s",
                        )
                        time.sleep(0.15)
                    t.join()
                    result = _result_holder[0]
                    elapsed = round(time.time() - start_time, 2)
                finally:
                    st.session_state.model_busy = False
                    st.session_state.busy_model_name = ""
                    st.session_state.busy_task = ""
                    if unload_model(selected_model or ""):
                        st.session_state._just_unloaded = True

                progress_bar.progress(1.0, text="✓ Done")
                time.sleep(0.3)
                progress_bar.empty()

                if result["success"]:
                    st.markdown(
                        f'<span class="status-badge status-success">✓ Analysis Complete · {elapsed}s</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown('<div class="section-header">Analysis Metrics</div>',
                                unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="metric-panel">
                        <div class="info-row">
                            <span class="info-key">Analysis Time</span>
                            <span class="info-val">{elapsed}s</span>
                        </div>
                        <div class="info-row">
                            <span class="info-key">Detected Language</span>
                            <span class="info-val">{result['language']}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-key">Model</span>
                            <span class="model-chip">{result.get('model_used','—')}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown('<div class="section-header">Complexity Results</div>',
                                unsafe_allow_html=True)
                    _render_result_panel(result)

                    # ── Complexity Visualization ──
                    st.markdown('<div class="section-header">Growth Curve Visualization</div>',
                                unsafe_allow_html=True)
                    try:
                        fig = build_complexity_chart(result["time_complexity"])
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as _ve:
                        st.caption(f"Chart error: {_ve}")

                    # ── Export ──
                    st.markdown('<div class="section-header">Export Report</div>',
                                unsafe_allow_html=True)
                    _render_export_buttons(result, code_input, key_prefix="block")

                    # ── Record history ──
                    _record_history(result, code_input, selected_model or "")
                else:
                    st.markdown(
                        '<span class="status-badge status-error">✗ Analysis Failed</span>',
                        unsafe_allow_html=True,
                    )
                    st.error(result["reasoning"])

                if getattr(st.session_state, "_just_unloaded", False):
                    st.caption("🔌 GPU memory freed — model unloaded from VRAM")
                    st.session_state._just_unloaded = False


# ███████████████████████████████████████████████████████████████████████████████
#  TAB 2 — SIDE-BY-SIDE COMPARE
# ███████████████████████████████████████████████████████████████████████████████

with tab_compare:
    st.markdown("""
    <div style="font-size:0.82rem;color:rgba(226,232,240,0.45);margin-bottom:1rem;">
        Paste two versions of your code and compare their Big-O complexities.
        Great for validating that your optimization actually improves things.
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2, gap="medium")

    with col_a:
        st.markdown('<div class="compare-header-a">▶ Version A — Original</div>',
                    unsafe_allow_html=True)
        code_a = st.text_area(
            "Code A",
            height=280,
            placeholder="# Paste your original / slower version here\n\ndef brute_force(arr):\n    for i in arr:\n        for j in arr:\n            ...",
            label_visibility="collapsed",
            key="compare_code_a",
        )

    with col_b:
        st.markdown('<div class="compare-header-b">▶ Version B — Optimized</div>',
                    unsafe_allow_html=True)
        code_b = st.text_area(
            "Code B",
            height=280,
            placeholder="# Paste your optimized version here\n\ndef optimized(arr):\n    seen = set()\n    for x in arr:\n        ...",
            label_visibility="collapsed",
            key="compare_code_b",
        )

    compare_clicked = st.button(
        "⚖️  Compare Complexities",
        use_container_width=False,
        key="compare_btn",
        disabled=st.session_state.model_busy,
    )

    if compare_clicked:
        if not code_a.strip() or not code_b.strip():
            st.warning("⚠  Paste code in both panels before comparing.")
        else:
            st.session_state.model_busy = True
            st.session_state.busy_model_name = selected_model or "unknown"
            st.session_state.busy_task = "Side-by-Side Compare"
            cmp_progress = st.progress(0, text="Analyzing Version A...")
            try:
                t0 = time.time()
                res_a = analyze_complexity(code_a, selected_language, selected_model)
                res_a["elapsed"] = round(time.time() - t0, 2)
                res_a["model_used"] = selected_model or "—"
                cmp_progress.progress(0.5, text="Analyzing Version B...")
                t0 = time.time()
                res_b = analyze_complexity(code_b, selected_language, selected_model)
                res_b["elapsed"] = round(time.time() - t0, 2)
                res_b["model_used"] = selected_model or "—"
                cmp_progress.progress(1.0, text="✓ Both versions analyzed")
                time.sleep(0.3)
            finally:
                st.session_state.model_busy = False
                if unload_model(selected_model or ""):
                    st.session_state._just_unloaded = True
            cmp_progress.empty()

            # ── Winner determination ──────────────────────────────────────
            if res_a["success"] and res_b["success"]:
                rank_a = _complexity_rank(res_a["time_complexity"])
                rank_b = _complexity_rank(res_b["time_complexity"])

                if rank_a < rank_b:
                    winner_html = '<div class="winner-banner winner-a">🏆 Version A is faster — <code>{}</code> &lt; <code>{}</code></div>'.format(
                        res_a["time_complexity"], res_b["time_complexity"])
                elif rank_b < rank_a:
                    winner_html = '<div class="winner-banner winner-b">🏆 Version B is faster — <code>{}</code> &lt; <code>{}</code></div>'.format(
                        res_b["time_complexity"], res_a["time_complexity"])
                else:
                    winner_html = '<div class="winner-banner winner-tie">🤝 Both versions have the same complexity — <code>{}</code></div>'.format(
                        res_a["time_complexity"])

                st.markdown(winner_html, unsafe_allow_html=True)
                
            if getattr(st.session_state, "_just_unloaded", False):
                st.caption("🔌 GPU memory freed — model unloaded from VRAM")
                st.session_state._just_unloaded = False

            # ── Side panels ───────────────────────────────────────────────
            col_res_a, col_res_b = st.columns(2, gap="medium")

            with col_res_a:
                if res_a["success"]:
                    st.markdown('<div class="section-header">Version A Results</div>',
                                unsafe_allow_html=True)
                    _render_result_panel(res_a, side_prefix="A", color="#00ADB5")
                else:
                    st.error(f"Version A failed: {res_a['reasoning']}")

            with col_res_b:
                if res_b["success"]:
                    st.markdown('<div class="section-header">Version B Results</div>',
                                unsafe_allow_html=True)
                    _render_result_panel(res_b, side_prefix="B", color="#a855f7")
                else:
                    st.error(f"Version B failed: {res_b['reasoning']}")


# ███████████████████████████████████████████████████████████████████████████████
#  TAB 3 — BATCH FILE ANALYSIS
# ███████████████████████████████████████████████████████████████████████████████

with tab_batch:
    st.markdown("""
    <div style="font-size:0.82rem;color:rgba(226,232,240,0.45);margin-bottom:1rem;">
        Upload a <code>.py</code> or <code>.cpp</code> file. Every function will be
        individually analyzed and displayed in a sortable complexity table.
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload source file",
        type=["py", "cpp", "c", "h", "cc", "cxx"],
        label_visibility="collapsed",
        key="batch_upload",
    )

    batch_clicked = st.button("📂  Analyze All Functions", key="batch_btn")

    if uploaded_file and batch_clicked:
        source_text = uploaded_file.read().decode("utf-8", errors="replace")
        filename = uploaded_file.name

        with st.spinner(f"Extracting functions from {filename}..."):
            functions = extract_functions(filename, source_text)

        if not functions:
            st.warning("No functions found in the uploaded file.")
        else:
            total = len(functions)
            st.markdown(
                f'<div class="section-header">Found {total} function{"s" if total != 1 else ""} — Analyzing…</div>',
                unsafe_allow_html=True,
            )

            st.session_state.model_busy = True
            st.session_state.busy_model_name = selected_model or "unknown"
            st.session_state.busy_task = f"Batch Analysis · {total} functions"
            progress_bar = st.progress(0, text="Starting batch analysis...")
            results_accumulator = []

            try:
                for idx, fn in enumerate(functions):
                    progress_bar.progress(
                        (idx + 1) / total,
                        text=f"⚙ Analyzing `{fn['name']}` ({idx+1}/{total})",
                    )
                    res = analyze_complexity(fn["code"], selected_language, selected_model)
                    res["function_name"] = fn["name"]
                    res["model_used"] = selected_model or "—"
                    results_accumulator.append(res)
            finally:
                st.session_state.model_busy = False
                st.session_state.busy_model_name = ""
                st.session_state.busy_task = ""
                if unload_model(selected_model or ""):
                    st.session_state._just_unloaded = True

            progress_bar.progress(1.0, text=f"✓ Analyzed {total} functions")
            time.sleep(0.4)
            progress_bar.empty()


            # ── Build results table ───────────────────────────────────────
            if getattr(st.session_state, "_just_unloaded", False):
                st.caption("🔌 GPU memory freed — model unloaded from VRAM")
                st.session_state._just_unloaded = False
                
            st.markdown(
                f'<span class="status-badge status-success">✓ Batch Analysis Complete — {total} functions</span>',
                unsafe_allow_html=True,
            )

            rows_html = ""
            for r in results_accumulator:
                fn_name = r.get("function_name", "?")
                time_cx = r.get("time_complexity", "—")
                space_cx = r.get("space_complexity", "—")
                best = r.get("best_case", "—")
                worst = r.get("worst_case", "—")
                opt = r.get("better_possible", "N/A")
                sug = r.get("suggested_algorithm", "N/A")
                ok = "✓" if r.get("success") else "✗"

                opt_class = "batch-opt-yes" if str(opt).upper() == "YES" else "batch-opt-no"
                opt_label = "Yes" if str(opt).upper() == "YES" else "No"

                rows_html += f"""
                <tr>
                    <td><span class="batch-fn-name">{fn_name}</span></td>
                    <td><span class="batch-complexity">{time_cx}</span></td>
                    <td>{space_cx}</td>
                    <td>{best}</td>
                    <td>{worst}</td>
                    <td><span class="{opt_class}">{opt_label}</span></td>
                    <td style="color:rgba(226,232,240,0.5);font-size:0.78rem;">{sug if sug != 'N/A' else '—'}</td>
                </tr>
                """

            table_html = f"""
            <div class="batch-table-wrap" style="margin-top:1rem;">
                <table class="batch-table">
                    <thead>
                        <tr>
                            <th>Function</th>
                            <th>Time O(·)</th>
                            <th>Space O(·)</th>
                            <th>Best Case</th>
                            <th>Worst Case</th>
                            <th>Optimizable?</th>
                            <th>Suggestion</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
            """
            st.markdown(table_html, unsafe_allow_html=True)

            # ── Expandable per-function details ──────────────────────────
            st.markdown('<div class="section-header">Per-Function Details</div>',
                        unsafe_allow_html=True)
            for r in results_accumulator:
                fn_name = r.get("function_name", "?")
                time_cx = r.get("time_complexity", "?")
                with st.expander(f"🔍  `{fn_name}` — {time_cx}"):
                    _render_result_panel(r)

    elif not uploaded_file and batch_clicked:
        st.warning("⚠  Upload a file before clicking Analyze.")


# ███████████████████████████████████████████████████████████████████████████████
#  TAB 4 — HISTORY
# ███████████████████████████████████████████████████████████████████████████████

with tab_history:
    history = st.session_state.history

    if not history:
        st.markdown("""
        <div style="text-align:center;padding:3rem 0;color:rgba(226,232,240,0.25);">
            <div style="font-size:2.5rem;margin-bottom:0.75rem">📜</div>
            <div style="font-size:0.9rem;font-weight:600;">No analyses yet</div>
            <div style="font-size:0.78rem;margin-top:0.3rem;">
                Run an analysis in the <b>Single Analysis</b> tab to see it here.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        hist_col, _ = st.columns([3, 1])
        with hist_col:
            if st.button("🗑 Clear History", key="clear_history"):
                st.session_state.history = []
                st.rerun()

        st.markdown(
            f'<div class="section-header">{len(history)} past analysis result{"s" if len(history) != 1 else ""}</div>',
            unsafe_allow_html=True,
        )

        for idx, entry in enumerate(history):
            time_cx = entry["time_complexity"]
            space_cx = entry["space_complexity"]
            conf = entry.get("confidence", 0.5)
            conf_pct = int(conf * 100)

            if conf >= 0.75:
                conf_color = "#22c55e"
            elif conf >= 0.45:
                conf_color = "#fbbf24"
            else:
                conf_color = "#ef4444"

            st.markdown(f"""
            <div class="hist-card">
                <div class="hist-meta">{entry['timestamp']} · <span style="color:#00ADB5">{entry['model']}</span> · {entry['language']}</div>
                <div>
                    <span class="hist-cx">{time_cx}</span>
                    <span class="hist-space">space: {space_cx}</span>
                    <span style="float:right;font-family:'JetBrains Mono',monospace;
                                font-size:0.72rem;color:{conf_color};font-weight:700;">
                        {conf_pct}% confidence
                    </span>
                </div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;
                            color:rgba(226,232,240,0.3);margin-top:0.4rem;
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                    {entry['code_snippet'].replace('<','&lt;').replace('>','&gt;')[:120]}
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"🔍 Full Result — Entry #{len(history) - idx}"):
                _render_result_panel(entry["result"])

                # Chart
                try:
                    fig = build_complexity_chart(time_cx)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass

                # Export
                st.markdown('<div class="section-header">Export</div>', unsafe_allow_html=True)
                _render_export_buttons(
                    entry["result"],
                    entry["code_snippet"],
                    key_prefix=f"hist_{idx}",
                )
