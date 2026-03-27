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

      div.stButton > button {
        border-radius: 999px;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.9);
      }

      div.stButton > button:hover {
        border-color: #d9b89a;
        color: var(--text);
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


def parse_course_list(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


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
        if mode == "Prerequisite Check":
            target_course = detect_course_in_prompt(prompt) or st.session_state.target_course
            result = assistant.check_eligibility(
                question=prompt,
                target_course=target_course,
                student_courses=parse_course_list(st.session_state.completed_courses),
            )
        elif mode == "Program / Policy QA":
            result = assistant.answer_question(prompt)
        else:
            result = assistant.generate_plan(
                {
                    "program": st.session_state.program,
                    "catalog_year": st.session_state.catalog_year,
                    "target_term": st.session_state.target_term,
                    "max_courses": int(st.session_state.max_courses),
                    "completed_courses": parse_course_list(st.session_state.completed_courses),
                }
            )
    add_message("assistant", result["formatted_response"], mode)


def render_assistant_message(content: str) -> None:
    sections = parse_response_sections(content)
    answer = sections["answer"] if isinstance(sections["answer"], str) else ""
    badge_text, badge_class = response_badge(answer)

    with st.chat_message("assistant", avatar="AI"):
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

        if why_items:
            st.markdown('<div class="section-label">Why</div>', unsafe_allow_html=True)
            for item in why_items:
                st.markdown(f"- {item}")

        if next_steps:
            st.markdown('<div class="section-label">Next steps</div>', unsafe_allow_html=True)
            for item in next_steps:
                st.markdown(f"- {item}")

        if citations:
            with st.expander(f"Citations ({len(citations)})", expanded=True):
                for item in citations:
                    label, url, section, accessed_date = parse_citation(item)
                    if section:
                        prefix = f"**[{label}]** " if label else ""
                        st.markdown(f"- {prefix}[{section}]({url})  \n  Accessed {accessed_date}")
                    else:
                        st.markdown(f"- {item}")

        if clarifying:
            with st.expander("Clarifying questions", expanded=True):
                for item in clarifying:
                    st.markdown(f"- {item}")

        if assumptions:
            with st.expander("Assumptions / not in catalog", expanded=not citations):
                for item in assumptions:
                    st.markdown(f"- {item}")


def render_user_message(content: str, mode: str) -> None:
    with st.chat_message("user", avatar="You"):
        st.caption(mode)
        st.markdown(content)


def render_quick_prompts() -> None:
    prompts = PROMPT_PRESETS[st.session_state.mode]
    columns = st.columns(len(prompts))
    for index, prompt in enumerate(prompts):
        if columns[index].button(prompt, key=f"preset_{st.session_state.mode}_{index}", use_container_width=True):
            st.session_state.queued_prompt = prompt


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
            st.session_state.queued_prompt = "Build my next term plan."

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []

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

queued_prompt = st.session_state.pop("queued_prompt", None)
typed_prompt = st.chat_input(
    {
        "Program / Policy QA": "Ask about major requirements, units, breadth, or Berkeley policy...",
        "Prerequisite Check": "Ask if you're eligible for a course or what the prerequisite chain looks like...",
        "Term Plan": "Ask for a next-term plan or use the Generate plan button in the sidebar...",
    }[st.session_state.mode]
)

if typed_prompt:
    queued_prompt = typed_prompt

if queued_prompt:
    run_current_request(assistant, queued_prompt)

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
