from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from orchestration import CoursePlanningAssistant  # noqa: E402
from utils import extract_course_codes  # noqa: E402


SECTION_MAP = {
    "Answer / Plan:": "answer",
    "Why (requirements/prereqs satisfied):": "why",
    "Citations:": "citations",
    "Clarifying questions (if needed):": "clarifying",
    "Assumptions / Not in catalog:": "assumptions",
}

PROMPT_PRESETS = {
    "Prerequisite Check": [
        "Can I take COMPSCI 170 if I've completed COMPSCI 61B and COMPSCI 70?",
        "What is the full prerequisite chain to reach COMPSCI 162 from scratch?",
        "Can I take COMPSCI 189 if I have MATH 53, MATH 54, and COMPSCI 70?",
    ],
    "Program / Policy QA": [
        "What breadth requirements do computer science students need to satisfy?",
        "What is the difference between the CS major and the CS minor?",
        "How many units must be completed in residence at the university?",
    ],
    "Term Plan": [
        "Build my next term plan.",
        "Recommend a conservative next-term schedule.",
        "What should I take next if I want to stay on track?",
    ],
}


st.set_page_config(
    page_title="Catalog Planner",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root {
        --bg-top: #f7f3eb;
        --bg-bottom: #efe7da;
        --panel: rgba(255, 252, 247, 0.88);
        --panel-strong: rgba(255, 255, 255, 0.96);
        --border: #e6dac7;
        --text: #241f19;
        --muted: #75695c;
        --accent: #c96f2d;
        --accent-soft: #fff2e6;
        --success: #1f7a55;
        --success-soft: #edf8f3;
        --warn: #8b5e13;
        --warn-soft: #fff8e8;
        --shadow: 0 18px 40px rgba(76, 58, 39, 0.08);
      }

      [data-testid="stAppViewContainer"] {
        background:
          radial-gradient(circle at top left, rgba(255, 245, 230, 0.95), transparent 28%),
          linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bottom) 100%);
      }

      [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(255, 250, 243, 0.94) 0%, rgba(249, 242, 232, 0.96) 100%);
        border-right: 1px solid var(--border);
      }

      [data-testid="stSidebar"] * {
        color: var(--text) !important;
      }

      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
      [data-testid="stSidebar"] label,
      [data-testid="stSidebar"] span {
        color: var(--text) !important;
      }

      [data-testid="stSidebar"] [data-testid="stAlertContainer"] {
        background: rgba(255, 244, 204, 0.96);
        border: 1px solid #eed28f;
        border-radius: 18px;
      }

      [data-testid="stSidebar"] [data-testid="stAlertContainer"] * {
        color: #5b4316 !important;
      }

      .block-container {
        max-width: 940px;
        padding-top: 1.4rem;
        padding-bottom: 6rem;
      }

      [data-testid="stChatMessage"] {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 0.6rem 0.9rem;
        box-shadow: var(--shadow);
        overflow: hidden;
      }

      .hero {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(255, 248, 240, 0.86));
        border: 1px solid var(--border);
        border-radius: 28px;
        padding: 1.3rem 1.4rem 1.2rem 1.4rem;
        box-shadow: var(--shadow);
        margin-bottom: 1rem;
      }

      .hero-kicker {
        display: inline-block;
        font-size: 0.76rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--accent);
        background: var(--accent-soft);
        border: 1px solid #f0d3b7;
        border-radius: 999px;
        padding: 0.28rem 0.62rem;
        margin-bottom: 0.8rem;
      }

      .hero h1 {
        font-size: 2.05rem;
        line-height: 1.08;
        margin: 0 0 0.45rem 0;
        color: var(--text);
      }

      .hero p {
        margin: 0;
        color: var(--muted);
        font-size: 1rem;
        line-height: 1.55;
      }

      .pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 1rem;
      }

      .pill {
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid var(--border);
        color: var(--text);
        border-radius: 999px;
        padding: 0.35rem 0.72rem;
        font-size: 0.84rem;
      }

      .response-shell {
        background: var(--panel-strong);
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 1rem 1.05rem;
        width: 100%;
        max-width: 100%;
        box-sizing: border-box;
      }

      .user-shell {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(252, 247, 240, 0.96));
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 0.9rem 1rem;
        width: 100%;
        max-width: 100%;
        box-sizing: border-box;
      }

      .user-mode {
        display: inline-block;
        color: #5d4a38;
        background: #f4e3d4;
        border: 1px solid #e7cdb4;
        border-radius: 10px;
        padding: 0.18rem 0.45rem;
        font-size: 0.82rem;
        font-weight: 600;
        margin-bottom: 0.6rem;
      }

      .user-body {
        color: var(--text);
        line-height: 1.6;
        font-size: 1.02rem;
        font-weight: 500;
      }

      .user-shell * {
        color: var(--text) !important;
      }

      .detail-card {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 0.9rem 1rem;
        margin-top: 0.85rem;
        width: 100%;
        max-width: 100%;
        box-sizing: border-box;
      }

      .detail-title {
        color: var(--muted);
        font-size: 0.76rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
        font-weight: 700;
      }

      .detail-list {
        margin: 0;
        padding-left: 1.1rem;
        color: var(--text);
      }

      .detail-list li {
        margin: 0 0 0.42rem 0;
        line-height: 1.65;
      }

      .detail-list li:last-child {
        margin-bottom: 0;
      }

      .citation-stack {
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
      }

      .citation-item {
        color: var(--text);
        line-height: 1.55;
      }

      .citation-item a {
        color: #1d5fbf !important;
        text-decoration: none;
        font-weight: 600;
      }

      .citation-item a:hover {
        text-decoration: underline;
      }

      .decision-badge {
        display: inline-block;
        border-radius: 999px;
        padding: 0.22rem 0.62rem;
        font-size: 0.76rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.8rem;
      }

      .decision-eligible {
        color: var(--success);
        background: var(--success-soft);
        border: 1px solid #ccebdc;
      }

      .decision-caution {
        color: var(--warn);
        background: var(--warn-soft);
        border: 1px solid #f0deb1;
      }

      .decision-plan {
        color: var(--accent);
        background: var(--accent-soft);
        border: 1px solid #f0d3b7;
      }

      .answer-body {
        color: var(--text);
        line-height: 1.65;
        font-size: 0.99rem;
      }

      .section-label {
        color: var(--muted);
        font-size: 0.77rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-top: 1rem;
        margin-bottom: 0.25rem;
      }

      .empty-state {
        text-align: center;
        padding: 2.2rem 1rem 1.2rem 1rem;
        color: var(--muted);
      }

      [data-testid="stMetricValue"],
      [data-testid="stMetricLabel"] {
        color: var(--text) !important;
      }

      [data-testid="stSidebar"] [role="radiogroup"] label {
        background: rgba(255, 255, 255, 0.68);
        border: 1px solid rgba(230, 218, 199, 0.92);
        border-radius: 14px;
        padding: 0.2rem 0.45rem;
        margin-bottom: 0.28rem;
      }

      [data-testid="stSidebar"] textarea,
      [data-testid="stSidebar"] input {
        color: var(--text) !important;
        background: rgba(255, 255, 255, 0.96) !important;
        border: 1px solid var(--border) !important;
      }

      [data-testid="stSidebar"] textarea::placeholder,
      [data-testid="stSidebar"] input::placeholder {
        color: #8f8478 !important;
      }

      div.stButton > button {
        border-radius: 999px;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.94);
        color: var(--text) !important;
        font-weight: 600;
        box-shadow: 0 8px 20px rgba(76, 58, 39, 0.06);
      }

      div.stButton > button:hover {
        border-color: #d9b89a;
        color: var(--text);
        background: rgba(255, 248, 240, 0.98);
      }

      div.stButton > button p,
      div.stButton > button span {
        color: var(--text) !important;
      }

      .composer-shell {
        position: sticky;
        bottom: 0;
        z-index: 10;
        background: linear-gradient(180deg, rgba(244, 237, 227, 0.2), rgba(244, 237, 227, 0.94) 22%, rgba(250, 246, 240, 0.98) 100%);
        padding-top: 0.9rem;
        margin-top: 1rem;
      }

      .composer-shell [data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.94);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 0.55rem 0.7rem 0.25rem 0.7rem;
        box-shadow: var(--shadow);
      }

      .composer-shell [data-testid="stTextInput"] input {
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
        caret-color: var(--text) !important;
        opacity: 1 !important;
        background: rgba(255, 255, 255, 0.98) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        font-weight: 500 !important;
      }

      .composer-shell [data-testid="stTextInput"] input::placeholder {
        color: #6f6459 !important;
        -webkit-text-fill-color: #6f6459 !important;
        opacity: 1 !important;
      }

      .composer-shell [data-testid="stTextInput"] label {
        display: none !important;
      }

      .composer-shell button[kind="secondaryFormSubmit"] {
        min-height: 2.75rem;
      }

      .composer-note {
        color: var(--muted);
        font-size: 0.86rem;
        margin: 0.15rem 0 0.35rem 0.15rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def load_assistant() -> CoursePlanningAssistant:
    return CoursePlanningAssistant.from_artifacts()


def init_state() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("mode", "Program / Policy QA")
    st.session_state.setdefault("target_course", "COMPSCI 170")
    st.session_state.setdefault("completed_courses", "COMPSCI 61A, COMPSCI 61B, COMPSCI 70")
    st.session_state.setdefault("program", "Computer Science")
    st.session_state.setdefault("catalog_year", "2024-2025")
    st.session_state.setdefault("target_term", "Fall")
    st.session_state.setdefault("max_courses", 3)
    st.session_state.setdefault("queued_prompt", None)
    st.session_state.setdefault("queued_prompt_nonce", 0)
    st.session_state.setdefault("last_processed_prompt_nonce", 0)
    st.session_state.setdefault("plan_request", "")


def parse_course_list(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def infer_plan_context_from_prompt(prompt: str) -> dict[str, str | int]:
    updates: dict[str, str | int] = {}
    lowered = prompt.strip().lower()

    if not lowered:
        return updates

    if any(token in lowered for token in ["cs minor", "computer science minor"]):
        updates["program"] = "Computer Science Minor"
    elif any(token in lowered for token in ["cs ba", "computer science ba", "computer science major", "computer science"]):
        updates["program"] = "Computer Science"
    elif "eecs" in lowered:
        updates["program"] = "EECS"

    catalog_match = re.search(r"\b(20\d{2}\s*-\s*20\d{2})\b", prompt)
    if catalog_match:
        updates["catalog_year"] = re.sub(r"\s+", "", catalog_match.group(1))

    for term in ["Fall", "Spring", "Summer"]:
        if term.lower() in lowered:
            updates["target_term"] = term
            break

    detected_courses = extract_course_codes(prompt)
    if detected_courses:
        updates["completed_courses"] = ", ".join(detected_courses)

    course_count_match = re.search(r"\b([1-6])\s*(?:courses?|classes?)\b", lowered)
    if course_count_match:
        updates["max_courses"] = int(course_count_match.group(1))
    elif lowered.isdigit() and 1 <= int(lowered) <= 6:
        updates["max_courses"] = int(lowered)

    return updates


def hydrate_term_plan_context(prompt: str) -> dict[str, str | int]:
    updates = infer_plan_context_from_prompt(prompt)
    for key, value in updates.items():
        st.session_state[key] = value
    return updates


def is_general_prompt(prompt: str) -> bool:
    lowered = prompt.lower().strip()
    patterns = [
        r"^\s*(hi|hello|hey|hii|yo)\b",
        r"\bhow are you\b",
        r"\bwhat can you do\b",
        r"^\s*help\s*$",
        r"\bthank you\b",
        r"^\s*thanks\s*$",
    ]
    return any(re.search(pattern, lowered) for pattern in patterns)


def queue_prompt(prompt: str) -> None:
    st.session_state.queued_prompt = prompt
    st.session_state.queued_prompt_nonce += 1


def submit_composer_prompt() -> None:
    prompt = st.session_state.get("composer_prompt_input", "").strip()
    if not prompt:
        return
    queue_prompt(prompt)
    st.session_state.composer_prompt_input = ""


def parse_response_sections(text: str) -> dict[str, list[str] | str]:
    sections: dict[str, list[str] | str] = {
        "answer": "",
        "why": [],
        "next_steps": [],
        "citations": [],
        "clarifying": [],
        "assumptions": [],
    }
    current_key: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line in SECTION_MAP:
            current_key = SECTION_MAP[line]
            continue
        if current_key == "answer":
            if line.startswith("Next step:"):
                sections["next_steps"].append(line.removeprefix("Next step:").strip())
            else:
                current_answer = sections["answer"]
                sections["answer"] = f"{current_answer}\n{line}".strip() if current_answer else line
            continue
        if current_key:
            item = line[2:].strip() if line.startswith("- ") else line
            if item and item.lower() != "none":
                current_items = sections[current_key]
                if isinstance(current_items, list):
                    current_items.append(item)
    return sections


def parse_citation(citation: str) -> tuple[str, str, str, str]:
    pattern = re.compile(r"^(?:\[(?P<label>C\d+)\]\s+)?\[Source:\s*(?P<url>[^,]+),\s*(?P<section>.*), accessed (?P<date>\d{4}-\d{2}-\d{2})\]$")
    match = pattern.match(citation.strip())
    if not match:
        return "", citation, "", ""
    return match.group("label") or "", match.group("url"), match.group("section"), match.group("date")


def render_detail_section(title: str, items: list[str]) -> None:
    if not items:
        return
    list_items = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    st.markdown(
        f"""
        <div class="detail-card">
          <div class="detail-title">{html.escape(title)}</div>
          <ul class="detail-list">{list_items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_citations_section(citations: list[str]) -> None:
    if not citations:
        return

    entries: list[str] = []
    seen: set[tuple[str, str]] = set()
    for item in citations:
        _, url, section, _ = parse_citation(item)
        if section and url:
            key = (url, section)
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                f'<div class="citation-item"><a href="{html.escape(url, quote=True)}" target="_blank">{html.escape(section)}</a></div>'
            )
        else:
            key = ("", item)
            if key in seen:
                continue
            seen.add(key)
            entries.append(f'<div class="citation-item">{html.escape(item)}</div>')

    st.markdown(
        f"""
        <div class="detail-card">
          <div class="detail-title">Citations</div>
          <div class="citation-stack">{''.join(entries)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def detect_course_in_prompt(prompt: str) -> str | None:
    match = re.search(r"\b(?:COMPSCI|MATH|EECS|DATA|STAT|PHYSICS|ENGIN)\s?[A-Z]?\d+[A-Z]{0,2}\b", prompt.upper())
    return match.group(0) if match else None


def response_badge(answer: str) -> tuple[str, str]:
    lowered = answer.lower()
    if lowered.startswith("eligible"):
        return "Eligible", "decision-eligible"
    if lowered.startswith("not eligible"):
        return "Not eligible", "decision-caution"
    if lowered.startswith("not in catalog") or "don't have that information" in lowered:
        return "Not in catalog", "decision-caution"
    if "plan" in lowered or "\n" in answer:
        return "Plan", "decision-plan"
    return "Grounded answer", "decision-plan"


def add_message(role: str, content: str, mode: str) -> None:
    st.session_state.messages.append({"role": role, "content": content, "mode": mode})


def run_current_request(assistant: CoursePlanningAssistant, prompt: str) -> None:
    mode = st.session_state.mode
    add_message("user", prompt, mode)

    with st.spinner("Checking Berkeley catalog records..."):
        if is_general_prompt(prompt):
            result = assistant.answer_question(prompt)
        elif mode == "Prerequisite Check":
            target_course = detect_course_in_prompt(prompt) or st.session_state.target_course
            result = assistant.check_eligibility(
                question=prompt,
                target_course=target_course,
                student_courses=parse_course_list(st.session_state.completed_courses),
            )
        elif mode == "Program / Policy QA":
            result = assistant.answer_question(prompt)
        else:
            updates = hydrate_term_plan_context(prompt)
            if prompt.strip() and (not updates or any(token in prompt.lower() for token in ["plan", "track", "light", "lighter", "conservative", "aggressive", "fewer", "more"])):
                st.session_state.plan_request = prompt.strip()
            result = assistant.generate_plan(
                {
                    "program": st.session_state.program,
                    "catalog_year": st.session_state.catalog_year,
                    "target_term": st.session_state.target_term,
                    "max_courses": int(st.session_state.max_courses),
                    "completed_courses": parse_course_list(st.session_state.completed_courses),
                    "request": st.session_state.plan_request,
                }
            )
    add_message("assistant", result["formatted_response"], mode)


def render_assistant_message(content: str) -> None:
    sections = parse_response_sections(content)
    answer = sections["answer"] if isinstance(sections["answer"], str) else ""
    badge_text, badge_class = response_badge(answer)

    with st.chat_message("assistant", avatar="🎓"):
        st.markdown(
            f"""
            <div class="response-shell">
              <div class="decision-badge {badge_class}">{html.escape(badge_text)}</div>
              <div class="answer-body">{html.escape(answer).replace(chr(10), "<br>")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        why_items = sections["why"] if isinstance(sections["why"], list) else []
        next_steps = sections["next_steps"] if isinstance(sections["next_steps"], list) else []
        clarifying = sections["clarifying"] if isinstance(sections["clarifying"], list) else []
        assumptions = sections["assumptions"] if isinstance(sections["assumptions"], list) else []
        citations = sections["citations"] if isinstance(sections["citations"], list) else []

        render_detail_section("Why", why_items)
        render_detail_section("Next steps", next_steps)
        render_citations_section(citations)
        render_detail_section("Clarifying questions", clarifying)
        render_detail_section("Assumptions / not in catalog", assumptions)


def render_user_message(content: str, mode: str) -> None:
    with st.chat_message("user", avatar="👤"):
        st.markdown(
            f"""
            <div class="user-shell">
              <div class="user-mode">{html.escape(mode)}</div>
              <div class="user-body">{html.escape(content).replace(chr(10), "<br>")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_quick_prompts() -> None:
    prompts = PROMPT_PRESETS[st.session_state.mode]
    columns = st.columns(len(prompts))
    for index, prompt in enumerate(prompts):
        if columns[index].button(prompt, key=f"preset_{st.session_state.mode}_{index}", use_container_width=True):
            queue_prompt(prompt)


init_state()

try:
    assistant = load_assistant()
except FileNotFoundError:
    st.error("Processed catalog records were not found. Populate `data/processed/` before using the demo.")
    st.stop()

with st.sidebar:
    st.markdown("### Workspace")
    st.caption("Chat-first interface over curated UC Berkeley catalog records.")
    if assistant.rag_enabled:
        st.success(f"RAG mode active: FAISS index loaded from `{assistant.index_path.name}`.")
    else:
        st.warning("Fallback mode active: build the FAISS index with `python src/build_index.py` for full retrieval-backed runtime.")
    st.session_state.mode = st.radio(
        "Assistant mode",
        ["Program / Policy QA", "Prerequisite Check", "Term Plan"],
        index=["Program / Policy QA", "Prerequisite Check", "Term Plan"].index(st.session_state.mode),
    )

    metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
    metric_col_1.metric("Courses", len(assistant.courses))
    metric_col_2.metric("Reqs", len(assistant.requirements))
    metric_col_3.metric("Policies", len(assistant.policies))

    st.markdown("### Student context")
    st.text_area(
        "Completed courses",
        key="completed_courses",
        help="Comma-separated. Grades are optional, for example `COMPSCI 61B:B`.",
        height=110,
    )

    if st.session_state.mode == "Prerequisite Check":
        st.text_input("Focus course", key="target_course")
        st.caption("The chat prompt can override this if you mention a course code directly.")

    if st.session_state.mode == "Term Plan":
        st.text_input("Program", key="program")
        st.text_input("Catalog year", key="catalog_year")
        st.selectbox("Target term", ["Fall", "Spring", "Summer"], key="target_term")
        st.slider("Max courses", min_value=1, max_value=6, key="max_courses")
        if st.button("Generate plan", use_container_width=True):
            queue_prompt("Build my next term plan.")

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.plan_request = ""
        st.session_state.queued_prompt = None
        st.session_state.queued_prompt_nonce = 0
        st.session_state.last_processed_prompt_nonce = 0

st.markdown(
    """
    <div class="hero">
      <div class="hero-kicker">Catalog-grounded Berkeley assistant</div>
      <h1>Course planning with citations, not guesses.</h1>
      <p>
        Ask prerequisite, degree-requirement, or next-term planning questions. The assistant answers from curated UC Berkeley
        catalog records and clearly marks anything that is not established in the provided policies.
      </p>
      <div class="pill-row">
        <span class="pill">Structured output</span>
        <span class="pill">Safe abstention</span>
        <span class="pill">Prerequisite chains</span>
        <span class="pill">Source-backed citations</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

render_quick_prompts()

if st.session_state.queued_prompt_nonce > st.session_state.last_processed_prompt_nonce:
    queued_prompt = st.session_state.queued_prompt
    st.session_state.last_processed_prompt_nonce = st.session_state.queued_prompt_nonce
    if queued_prompt:
        run_current_request(assistant, queued_prompt)
        st.session_state.queued_prompt = None

if not st.session_state.messages:
    st.markdown(
        """
        <div class="empty-state">
          Start with a question above or use one of the quick prompts.
        </div>
        """,
        unsafe_allow_html=True,
    )

for message in st.session_state.messages:
    if message["role"] == "user":
        render_user_message(message["content"], message["mode"])
    else:
        render_assistant_message(message["content"])

st.markdown('<div class="composer-shell">', unsafe_allow_html=True)
composer_columns = st.columns([8, 1.2])
prompt_placeholder = {
    "Program / Policy QA": "Ask about major requirements, units, breadth, or Berkeley policy...",
    "Prerequisite Check": "Ask if you're eligible for a course or what the prerequisite chain looks like...",
    "Term Plan": "Ask for a next-term plan or continue the planning conversation...",
}[st.session_state.mode]
composer_columns[0].text_input(
    "Message",
    value=st.session_state.get("composer_prompt_input", ""),
    placeholder=prompt_placeholder,
    label_visibility="collapsed",
    key="composer_prompt_input",
)
composer_columns[1].button("Send", use_container_width=True, on_click=submit_composer_prompt)

st.markdown(
    f'<div class="composer-note">{html.escape(prompt_placeholder)}</div></div>',
    unsafe_allow_html=True,
)
