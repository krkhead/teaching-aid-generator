"""Teaching Aid Generator - simplified Streamlit UI."""

import re
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from config import CURRICULA, DIFFICULTIES, DOC_LABELS, EXTRA_FIELDS, FIELD_PROMPTS, DocType
from generate_content import build_prompt, generate_with_groq, sanitize_input
from generate_pdf import build_pdf
from image_gen import extract_image_directives, should_generate_real_images


STAGE_LABELS = {
    0: "Ready",
    1: "Researching",
    2: "Drafting",
    3: "Building PDF",
    4: "Complete",
}


def init_state() -> None:
    defaults = {
        "generation_stage": 0,
        "is_generating": False,
        "result": None,
        "activity_log": ["Ready to generate."],
        "last_image_directives": [],
        "last_generated_at": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def add_log(message: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.activity_log.append(f"[{stamp}] {message}")
    st.session_state.activity_log = st.session_state.activity_log[-12:]


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container { max-width: 1280px; padding-top: 1.25rem; }
        .app-shell { padding: 0.25rem 0 1rem; }
        .subtle { color: #475569; font-size: 0.95rem; }
        .status-bar {
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 0.9rem 1rem;
            background: #f8fafc;
            margin-bottom: 1rem;
        }
        .status-title { font-weight: 700; margin-bottom: 0.25rem; }
        .preview-card {
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 1rem 1.1rem;
            background: white;
        }
        .image-block {
            margin: 1rem 0;
            padding: 0.95rem 1rem;
            border: 1px dashed #93c5fd;
            border-radius: 14px;
            background: #f8fbff;
        }
        .image-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #2563eb;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }
        .log-box {
            border: 1px solid #dbeafe;
            background: #0f172a;
            color: #dbeafe;
            border-radius: 14px;
            padding: 0.85rem 1rem;
            font-family: Consolas, monospace;
            font-size: 0.82rem;
            min-height: 180px;
        }
        .log-box div { margin-bottom: 0.35rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def split_blocks(content: str) -> list[tuple[str, str]]:
    blocks = []
    buffer = []
    pattern = re.compile(r"\[GENERATE IMAGE:\s*(.+?)\]")
    for line in content.splitlines():
        match = pattern.search(line)
        if not match:
            buffer.append(line)
            continue
        before = line[:match.start()].rstrip()
        after = line[match.end():].lstrip()
        if before:
            buffer.append(before)
        if buffer:
            blocks.append(("markdown", "\n".join(buffer).strip()))
            buffer = []
        blocks.append(("image", match.group(1).strip()))
        if after:
            buffer.append(after)
    if buffer:
        blocks.append(("markdown", "\n".join(buffer).strip()))
    return [block for block in blocks if block[1]]


def render_status() -> None:
    stage = st.session_state.generation_stage
    stage_name = STAGE_LABELS[stage]
    st.markdown(
        f"""
        <div class="status-bar">
            <div class="status-title">Status: {stage_name}</div>
            <div class="subtle">Researching → Drafting → Building PDF</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    progress_map = {0: 0, 1: 20, 2: 65, 3: 90, 4: 100}
    st.progress(progress_map[stage] / 100)


def render_preview(result: dict | None) -> None:
    st.markdown('<div class="preview-card">', unsafe_allow_html=True)
    st.subheader("Preview")

    if not result:
        st.write("Your generated content will appear here.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    values = result["field_values"]
    meta = " | ".join(
        value
        for value in [values.get("subject"), values.get("class_level"), values.get("curriculum")]
        if value and value != "N/A"
    )
    if meta:
        st.caption(meta)

    for kind, payload in split_blocks(result["content"]):
        if kind == "markdown":
            st.markdown(payload)
        else:
            status = (
                "Will try Google image generation during PDF export."
                if should_generate_real_images()
                else "No Google API key found. PDF export will use a styled placeholder."
            )
            st.markdown(
                f"""
                <div class="image-block">
                    <div class="image-label">Image Block</div>
                    <div>{payload}</div>
                    <div style="margin-top:0.4rem; color:#475569;">{status}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


def render_log() -> None:
    st.subheader("Activity Log")
    rows = "".join(f"<div>{entry}</div>" for entry in st.session_state.activity_log)
    st.markdown(f'<div class="log-box">{rows}</div>', unsafe_allow_html=True)


def collect_values(doc_type: DocType, curr_key: str, diff_key: str) -> dict[str, str]:
    values = {}
    fields = ["subject", "class_level"] + EXTRA_FIELDS.get(doc_type, []) + ["instructions"]
    for field in fields:
        raw = st.session_state.get(f"field_{field}", "").strip()
        values[field] = sanitize_input(raw) if raw else "N/A"
    values["curriculum"] = CURRICULA[curr_key][0]
    values["difficulty"] = DIFFICULTIES[diff_key]
    return values


def run_generation(doc_type: DocType, values: dict[str, str]) -> None:
    st.session_state.result = None
    st.session_state.is_generating = True
    st.session_state.generation_stage = 1
    st.session_state.activity_log = []

    add_log(f"Starting {DOC_LABELS[doc_type]}.")
    add_log(f"Curriculum: {values['curriculum']}. Difficulty: {values['difficulty']}.")

    def on_progress(event: dict) -> None:
        name = event.get("event")
        if name == "llm_call_started":
            st.session_state.generation_stage = 2
            add_log(f"Generating: {event.get('label', 'Drafting')}.")
        elif name == "continuation_requested":
            add_log(f"Fetching continuation {event.get('continuation_number')}/2.")
        elif name == "chunk_completed":
            add_log(f"Chunk {event.get('chunk_number')} complete.")
        elif name == "llm_call_completed" and event.get("total_tokens"):
            add_log(f"Tokens used: {event['total_tokens']}.")

    try:
        content = generate_with_groq(build_prompt(doc_type, values), progress_callback=on_progress)
    except ValueError as error:
        st.session_state.is_generating = False
        st.session_state.generation_stage = 0
        add_log(f"Configuration error: {error}")
        st.error(f"Configuration error: {error}")
        return
    except Exception as error:
        st.session_state.is_generating = False
        st.session_state.generation_stage = 0
        add_log(f"Groq error: {error}")
        st.error(f"Groq API error: {error}")
        return

    st.session_state.last_image_directives = extract_image_directives(content)
    add_log(f"Image blocks found: {len(st.session_state.last_image_directives)}.")
    st.session_state.generation_stage = 3
    add_log("Building PDF export.")

    try:
        subject_slug = values.get("subject", "document")[:40].lower().replace(" ", "_")
        stem = f"{doc_type.value}_{subject_slug}"
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / f"{stem}.md"
            pdf_path = Path(tmpdir) / f"{stem}.pdf"
            md_path.write_text(content, encoding="utf-8")
            build_pdf(md_path, pdf_path, doc_type_label=DOC_LABELS[doc_type])
            pdf_bytes = pdf_path.read_bytes()
    except Exception as error:
        st.session_state.is_generating = False
        st.session_state.generation_stage = 2
        add_log(f"PDF error: {error}")
        st.error(f"PDF generation failed: {error}")
        return

    st.session_state.result = {
        "pdf_bytes": pdf_bytes,
        "md_bytes": content.encode("utf-8"),
        "stem": stem,
        "content": content,
        "field_values": values,
    }
    st.session_state.is_generating = False
    st.session_state.generation_stage = 4
    st.session_state.last_generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    add_log("Done.")


st.set_page_config(page_title="Teaching Aid Generator", page_icon=":books:", layout="wide")
init_state()
inject_styles()

st.title("Teaching Aid Generator")
st.caption("Create a teaching document, preview it, then download PDF or Markdown.")

doc_col, preview_col = st.columns([0.95, 1.35], gap="large")

with doc_col:
    st.subheader("1. Fill in the details")

    current_doc = doc_type_from_value = next(
        (dt for dt in DocType if dt.value == st.session_state.get("selected_doc_type", DocType.TEXTBOOK.value)),
        DocType.TEXTBOOK,
    )
    current_curr = st.session_state.get("selected_curriculum", "1")
    current_diff = st.session_state.get("selected_difficulty", "2")

    doc_type = st.selectbox(
        "Document Type",
        list(DocType),
        index=list(DocType).index(current_doc),
        format_func=lambda item: DOC_LABELS[item],
    )
    curr_key = st.selectbox(
        "Curriculum / Examining Body",
        list(CURRICULA.keys()),
        index=list(CURRICULA.keys()).index(current_curr),
        format_func=lambda key: CURRICULA[key][1],
    )
    diff_key = st.selectbox(
        "Difficulty",
        list(DIFFICULTIES.keys()),
        index=list(DIFFICULTIES.keys()).index(current_diff),
        format_func=lambda key: DIFFICULTIES[key],
    )

    st.session_state.selected_doc_type = doc_type.value
    st.session_state.selected_curriculum = curr_key
    st.session_state.selected_difficulty = diff_key

    fields = ["subject", "class_level"] + EXTRA_FIELDS.get(doc_type, []) + ["instructions"]
    for field in fields:
        label = FIELD_PROMPTS.get(field, field.replace("_", " ").title())
        key = f"field_{field}"
        if field == "instructions":
            st.text_area(
                label,
                key=key,
                height=120,
                placeholder="Optional: Include Nigerian examples, diagrams, exam tips, or practical activities.",
            )
        else:
            st.text_input(label, key=key)

    values = collect_values(doc_type, curr_key, diff_key)

    st.subheader("2. Generate")
    if should_generate_real_images():
        st.caption("Google image generation is enabled for PDF export.")
    else:
        st.caption("Google image generation is not configured. Image prompts will become placeholders in the PDF.")

    if st.button("Generate Teaching Aid", type="primary", use_container_width=True):
        run_generation(doc_type, values)

with preview_col:
    st.subheader("3. Review and download")
    render_status()
    render_preview(st.session_state.result)

    if st.session_state.result:
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "Download PDF",
                st.session_state.result["pdf_bytes"],
                file_name=f'{st.session_state.result["stem"]}.pdf',
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
        with c2:
            st.download_button(
                "Export Markdown",
                st.session_state.result["md_bytes"],
                file_name=f'{st.session_state.result["stem"]}.md',
                mime="text/markdown",
                use_container_width=True,
            )
        if st.session_state.last_generated_at:
            st.caption(f"Last generated: {st.session_state.last_generated_at}")

render_log()
