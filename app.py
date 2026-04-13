"""Teaching Aid Generator studio UI."""

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


STEP_TEXT = {
    0: "Blueprint ready for a new run.",
    1: "Researching the brief and syllabus fit.",
    2: "Drafting and stitching long-form chunks.",
    3: "Polishing exports and media blocks.",
    4: "Studio output is ready.",
}


def init_state() -> None:
    defaults = {
        "activity_log": ["Studio boot complete.", "Awaiting blueprint input."],
        "generation_stage": 0,
        "is_generating": False,
        "result": None,
        "last_image_directives": [],
        "last_generated_at": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def log(message: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.activity_log.append(f"[{stamp}] {message}")
    st.session_state.activity_log = st.session_state.activity_log[-10:]


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Merriweather:wght@700&display=swap');
        .stApp { background: linear-gradient(180deg, #f4f7fb 0%, #edf2f7 100%); color: #0f172a; }
        .block-container { max-width: 1420px; padding-top: 1.2rem; padding-bottom: 2rem; }
        p, label, li, h1, h2, h3, h4 { font-family: 'Inter', sans-serif !important; }
        .shell, .card, .surface, .terminal { border: 1px solid rgba(148,163,184,.22); box-shadow: 0 20px 60px rgba(15,23,42,.08); }
        .shell { background: rgba(255,255,255,.72); border-radius: 28px; padding: 1.1rem; }
        .hero { border-radius: 22px; padding: 1rem 1.1rem; color: white; background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #315f8f 100%); margin-bottom: 1rem; }
        .hero h1 { margin: 0; font-size: 1.2rem; font-weight: 800; }
        .hero p { margin: .3rem 0 0; color: rgba(226,232,240,.82); }
        .card { background: rgba(255,255,255,.88); border-radius: 24px; padding: 1rem 1.1rem; }
        .kicker { text-transform: uppercase; letter-spacing: .18em; font-size: .72rem; color: #64748b; font-weight: 700; margin-bottom: .35rem; }
        .title { font-size: 1.02rem; font-weight: 700; color: #0f172a; margin-bottom: .9rem; }
        .metrics { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: .8rem; margin-bottom: 1rem; }
        .metric { background: linear-gradient(180deg,#f8fafc,#f1f5f9); border: 1px solid #e2e8f0; border-radius: 18px; padding: .9rem 1rem; }
        .metric strong { display:block; font-size:.75rem; text-transform:uppercase; letter-spacing:.12em; color:#64748b; margin-bottom:.35rem; }
        .step-grid { display:grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: .8rem; }
        .step { border-radius: 18px; border: 1px solid #cbd5e1; background: #f8fafc; padding: .9rem 1rem; }
        .step.active { border-color: rgba(59,130,246,.25); background: #eff6ff; }
        .step.done { background: #eef2ff; }
        .badge { width: 2rem; height: 2rem; border-radius: 999px; display:inline-flex; align-items:center; justify-content:center; background:#e2e8f0; font-weight:800; margin-bottom:.7rem; }
        .step.active .badge { background:#2563eb; color:white; }
        .surface { background: rgba(255,255,255,.92); border-radius: 28px; padding: 1.2rem; min-height: 72vh; }
        .page { border-radius: 24px; min-height: 62vh; border: 1px solid #cbd5e1; padding: 2rem; background: linear-gradient(180deg, rgba(248,250,252,.82), rgba(255,255,255,.97)); }
        .eyebrow { text-transform: uppercase; letter-spacing: .18em; font-size: .72rem; color: #64748b; font-weight: 700; margin-bottom: .7rem; }
        .page h2 { font-family: 'Merriweather', serif !important; font-size: 2.2rem; line-height: 1.15; margin: 0 0 .5rem; }
        .sub { color:#475569; padding-bottom:1rem; border-bottom:1px solid #e2e8f0; margin-bottom:1.3rem; }
        .empty { min-height: 48vh; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; color:#64748b; }
        .skeleton { height: 18px; border-radius: 14px; background: linear-gradient(90deg, #e2e8f0, #f8fafc, #e2e8f0); background-size: 220% 100%; animation: shimmer 1.6s linear infinite; margin-bottom: .9rem; }
        .image { margin: 1.5rem 0; padding: 1.1rem; border-radius: 22px; border: 1.5px dashed rgba(59,130,246,.34); background: linear-gradient(135deg,#eff6ff,#f8fafc); }
        .image span { display:inline-flex; font-size:.75rem; text-transform:uppercase; letter-spacing:.14em; color:#2563eb; background:white; border:1px solid #bfdbfe; border-radius:999px; padding:.32rem .7rem; }
        .image p { margin: .9rem 0 .7rem; color:#1e293b; }
        .status { display:inline-block; padding:.42rem .7rem; border-radius:999px; background:#dbeafe; color:#1d4ed8; font-size:.82rem; }
        .warn { background:#fef9c3; color:#854d0e; }
        .terminal { background: linear-gradient(180deg,#020617,#0f172a); color:#cbd5e1; border-radius: 20px; padding: .95rem 1rem; font-family: Consolas, monospace; font-size:.82rem; min-height: 180px; margin-top: 1rem; }
        .terminal div { margin-bottom: .45rem; }
        .terminal b { color:#22c55e; }
        @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -20% 0; } }
        @media (max-width: 1024px) { .metrics, .step-grid { grid-template-columns: 1fr; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def doc_type_from_value(value: str) -> DocType:
    for doc_type in DocType:
        if doc_type.value == value:
            return doc_type
    return DocType.TEXTBOOK


def render_metrics(doc_type: DocType, curr_key: str, diff_key: str) -> None:
    media = "Google image rendering on" if should_generate_real_images() else "Placeholder export mode"
    st.markdown(
        f"""
        <div class="metrics">
            <div class="metric"><strong>Document Mode</strong>{DOC_LABELS[doc_type]}</div>
            <div class="metric"><strong>Academic Profile</strong>{CURRICULA[curr_key][0]} · {DIFFICULTIES[diff_key]}</div>
            <div class="metric"><strong>Media Pipeline</strong>{media}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stepper(stage: int) -> None:
    steps = []
    names = ["Researching", "Drafting", "Polishing"]
    copy = [
        "Prompt framing and curriculum alignment.",
        "Chunked generation and continuity handling.",
        "PDF assembly and image treatment.",
    ]
    for idx, name in enumerate(names, start=1):
        klass = "done" if stage > idx else "active" if stage == idx else ""
        steps.append(f'<div class="step {klass}"><div class="badge">{idx}</div><div><b>{name}</b></div><div>{copy[idx-1]}</div></div>')
    st.markdown(
        f'<div class="card"><div class="kicker">Studio Status</div><div class="title">{STEP_TEXT[stage]}</div><div class="step-grid">{"".join(steps)}</div></div>',
        unsafe_allow_html=True,
    )


def render_skeleton() -> None:
    st.markdown('<div class="surface"><div class="page">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Canvas Preview</div><h2>AI is stitching your teaching aid</h2><div class="sub">The studio updates as Groq returns chunks and the export pipeline finishes.</div>', unsafe_allow_html=True)
    for height in ["52px", "18px", "18px", "18px", "200px", "18px", "18px", "120px"]:
        st.markdown(f'<div class="skeleton" style="height:{height};"></div>', unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)


def render_empty() -> None:
    st.markdown(
        """
        <div class="surface"><div class="page"><div class="empty">
            <div class="eyebrow">Canvas Preview</div>
            <h3>Blueprint the document, then generate the first draft.</h3>
            <p>The preview, image blocks, activity log, and exports will appear here.</p>
        </div></div></div>
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


def render_image(prompt: str) -> None:
    if should_generate_real_images():
        status = '<div class="status">Prepared for Google image rendering during export</div>'
    else:
        status = '<div class="status warn">No Google API key found. PDF export will keep a styled placeholder</div>'
    st.markdown(
        f'<div class="image"><span>Image block</span><p>{prompt}</p>{status}</div>',
        unsafe_allow_html=True,
    )


def render_document(result: dict) -> None:
    values = result["field_values"]
    subtitle = " · ".join(
        bit for bit in [values.get("subject"), values.get("class_level"), values.get("curriculum")] if bit and bit != "N/A"
    )
    st.markdown('<div class="surface"><div class="page">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="eyebrow">Generated Draft</div><h2>{DOC_LABELS[doc_type_from_value(result["doc_type"])]}</h2><div class="sub">{subtitle}</div>',
        unsafe_allow_html=True,
    )
    for kind, payload in split_blocks(result["content"]):
        if kind == "markdown":
            st.markdown(payload)
        else:
            render_image(payload)
    if not st.session_state.last_image_directives:
        st.info("No image directives were generated in this draft. Add visual requests in Special Instructions if you want more illustrated sections.")
    st.markdown("</div></div>", unsafe_allow_html=True)


def render_log() -> None:
    rows = "".join(f"<div><b>&gt;</b> {entry}</div>" for entry in st.session_state.activity_log)
    st.markdown(f'<div class="terminal">{rows}</div>', unsafe_allow_html=True)


def collect_values(doc_type: DocType, curr_key: str, diff_key: str) -> dict[str, str]:
    values = {}
    fields = ["subject", "class_level"] + EXTRA_FIELDS.get(doc_type, []) + ["instructions"]
    for field in fields:
        raw = st.session_state.get(f"field_{field}", "").strip()
        values[field] = sanitize_input(raw) if raw else "N/A"
    values["curriculum"] = CURRICULA[curr_key][0]
    values["difficulty"] = DIFFICULTIES[diff_key]
    return values


def run_generation(doc_type: DocType, values: dict[str, str], stepper_slot, canvas_slot) -> None:
    st.session_state.result = None
    st.session_state.is_generating = True
    st.session_state.generation_stage = 1
    st.session_state.activity_log = []
    st.session_state.last_image_directives = []
    log("Blueprint accepted.")
    log(f"Document mode: {DOC_LABELS[doc_type]}.")
    log(f"Curriculum target: {values['curriculum']} at {values['difficulty']} difficulty.")

    def refresh() -> None:
        with stepper_slot.container():
            render_stepper(st.session_state.generation_stage)
        with canvas_slot.container():
            render_skeleton()

    refresh()

    def on_progress(event: dict) -> None:
        name = event.get("event")
        if name == "llm_call_started":
            st.session_state.generation_stage = 2
            log(f"Groq call started: {event.get('label', 'Drafting')}.")
        elif name == "llm_call_completed":
            total = event.get("total_tokens")
            suffix = f" ({total} total tokens)" if total else ""
            log(f"Groq returned {event.get('finish_reason', 'unknown')} for {event.get('label', 'request')}{suffix}.")
        elif name == "continuation_requested":
            log(f"Context window reached. Fetching continuation {event.get('continuation_number')}/2.")
        elif name == "chunk_completed":
            log(f"Chunk {event.get('chunk_number')} stitched with finish reason: {event.get('finish_reason', 'unknown')}.")
        refresh()

    try:
        content = generate_with_groq(build_prompt(doc_type, values), progress_callback=on_progress)
    except ValueError as error:
        st.session_state.is_generating = False
        st.session_state.generation_stage = 0
        log(f"Configuration error: {error}")
        st.error(f"Configuration error: {error}")
        return
    except Exception as error:
        st.session_state.is_generating = False
        st.session_state.generation_stage = 0
        log(f"Groq API error: {error}")
        st.error(f"Groq API error: {error}")
        return

    st.session_state.last_image_directives = extract_image_directives(content)
    log(f"Detected {len(st.session_state.last_image_directives)} visual prompt(s) in the draft.")
    st.session_state.generation_stage = 3
    log("Building PDF export.")
    with stepper_slot.container():
        render_stepper(st.session_state.generation_stage)

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
        log(f"PDF build failed: {error}")
        st.error(f"PDF generation failed: {error}")
        return

    st.session_state.result = {
        "pdf_bytes": pdf_bytes,
        "md_bytes": content.encode("utf-8"),
        "stem": stem,
        "content": content,
        "field_values": values,
        "doc_type": doc_type.value,
    }
    st.session_state.is_generating = False
    st.session_state.generation_stage = 4
    st.session_state.last_generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log("Document ready. Exports compiled successfully.")

    with stepper_slot.container():
        render_stepper(st.session_state.generation_stage)
    with canvas_slot.container():
        render_document(st.session_state.result)


st.set_page_config(page_title="Teaching Aid Studio", page_icon=":books:", layout="wide")
init_state()
inject_styles()

current_doc = doc_type_from_value(st.session_state.get("selected_doc_type", DocType.TEXTBOOK.value))
current_curr = st.session_state.get("selected_curriculum", "1")
current_diff = st.session_state.get("selected_difficulty", "2")

st.markdown('<div class="shell">', unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>Teaching Aid Studio</h1><p>Blueprint, generate, preview, and export long-form teaching materials in one workspace.</p></div>', unsafe_allow_html=True)
render_metrics(current_doc, current_curr, current_diff)

left, right = st.columns([0.92, 1.68], gap="large")

with left:
    st.markdown('<div class="card"><div class="kicker">Blueprint</div><div class="title">Configure the teaching aid</div>', unsafe_allow_html=True)
    doc_type = st.selectbox("Document Type", list(DocType), index=list(DocType).index(current_doc), format_func=lambda item: DOC_LABELS[item])
    curr_key = st.selectbox("Curriculum / Examining Body", list(CURRICULA.keys()), index=list(CURRICULA.keys()).index(current_curr), format_func=lambda key: CURRICULA[key][1])
    diff_key = st.selectbox("Difficulty", list(DIFFICULTIES.keys()), index=list(DIFFICULTIES.keys()).index(current_diff), format_func=lambda key: DIFFICULTIES[key])
    st.session_state.selected_doc_type = doc_type.value
    st.session_state.selected_curriculum = curr_key
    st.session_state.selected_difficulty = diff_key

    fields = ["subject", "class_level"] + EXTRA_FIELDS.get(doc_type, []) + ["instructions"]
    for field in fields:
        label = FIELD_PROMPTS.get(field, field.replace("_", " ").title())
        key = f"field_{field}"
        if field == "instructions":
            st.text_area(label, key=key, height=140, placeholder="Include Nigerian examples, ask for diagrams, or specify tone and exam style.")
        else:
            st.text_input(label, key=key, placeholder=label)

    st.caption("Google image rendering is available during export." if should_generate_real_images() else "Add a Google API key to enable live image rendering during PDF export.")
    generate_now = st.button("Generate Studio Draft", use_container_width=True, type="primary")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    stepper_slot = st.empty()
    canvas_slot = st.empty()

values = collect_values(doc_type, curr_key, diff_key)

if generate_now:
    run_generation(doc_type, values, stepper_slot, canvas_slot)
else:
    with stepper_slot.container():
        render_stepper(st.session_state.generation_stage)
    with canvas_slot.container():
        if st.session_state.result:
            render_document(st.session_state.result)
        elif st.session_state.is_generating:
            render_skeleton()
        else:
            render_empty()

render_log()

if st.session_state.result:
    st.markdown('<div class="card"><div class="kicker">Quick Actions</div><div class="title">Export or run the blueprint again</div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    with a:
        rerun = st.button("Regenerate Draft", use_container_width=True)
    with b:
        st.download_button("Export Markdown", st.session_state.result["md_bytes"], file_name=f'{st.session_state.result["stem"]}.md', mime="text/markdown", use_container_width=True)
    with c:
        st.download_button("Download PDF", st.session_state.result["pdf_bytes"], file_name=f'{st.session_state.result["stem"]}.pdf', mime="application/pdf", use_container_width=True, type="primary")
    st.markdown("</div>", unsafe_allow_html=True)
    if st.session_state.last_generated_at:
        st.caption(f"Last successful generation: {st.session_state.last_generated_at}")
    if rerun:
        run_generation(doc_type, values, stepper_slot, canvas_slot)

st.markdown("</div>", unsafe_allow_html=True)
