"""Interactive CLI that collects user inputs and generates teaching aid content via Groq."""

import os
import re
import sys
from pathlib import Path
from typing import Callable, Optional

from dotenv import load_dotenv
from groq import Groq
from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live

_console = Console()

load_dotenv(Path(__file__).resolve().parent / ".env")

from config import (
    CURRICULA,
    DIFFICULTIES,
    EXTRA_FIELDS,
    FIELD_PROMPTS,
    SYSTEM_PROMPT,
    TEMPLATES,
    DOC_LABELS,
    DocType,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def pick_doc_type() -> DocType:
    print("\n╔══════════════════════════════════════════╗")
    print("║   TEACHING AID GENERATOR                 ║")
    print("╚══════════════════════════════════════════╝\n")
    print("What would you like to generate?\n")
    options = list(DocType)
    for i, dt in enumerate(options, 1):
        print(f"  [{i}] {DOC_LABELS[dt]}")
    while True:
        choice = input(f"\nEnter choice (1-{len(options)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            selected = options[int(choice) - 1]
            print(f"\n→ Selected: {DOC_LABELS[selected]}\n")
            return selected
        print("  Invalid choice. Try again.")


def pick_curriculum() -> str:
    """Let the user select an examining body / curriculum standard."""
    print("─── Curriculum / Examining Body ───\n")
    for key, (code, label) in CURRICULA.items():
        print(f"  [{key:>2}] {label}")
    while True:
        choice = input(f"\nEnter choice (1-{len(CURRICULA)}): ").strip()
        if choice in CURRICULA:
            code, label = CURRICULA[choice]
            print(f"\n→ Curriculum: {label}\n")
            return code
        print("  Invalid choice. Try again.")


def pick_difficulty() -> str:
    """Let the user select a difficulty level."""
    print("─── Difficulty ───\n")
    for key, label in DIFFICULTIES.items():
        print(f"  [{key}] {label}")
    while True:
        choice = input(f"\nEnter choice (1-{len(DIFFICULTIES)}): ").strip()
        if choice in DIFFICULTIES:
            selected = DIFFICULTIES[choice]
            print(f"\n→ Difficulty: {selected}\n")
            return selected
        print("  Invalid choice. Try again.")


def sanitize_input(value: str, max_length: int = 200) -> str:
    """Strip control characters and newlines; limit length to prevent prompt injection."""
    # Remove all control characters except regular space and tab
    cleaned = re.sub(r"[\x00-\x08\x0a-\x1f\x7f]", "", value)
    # Collapse multiple spaces/tabs into one
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    return cleaned[:max_length]


def collect_inputs(doc_type: DocType) -> dict[str, str]:
    """Prompt the user for each required field."""
    extra = EXTRA_FIELDS.get(doc_type, [])
    fields = ["subject", "class_level"] + extra + ["instructions"]

    inputs: dict[str, str] = {}
    print("─── Fill in the details ───\n")
    for field in fields:
        prompt_text = FIELD_PROMPTS.get(field, field.replace("_", " ").title())
        raw = input(f"  {prompt_text}: ").strip()
        value = sanitize_input(raw)
        inputs[field] = value if value else "N/A"
    return inputs


def build_prompt(doc_type: DocType, inputs: dict[str, str]) -> str:
    """Fill the template with collected inputs, ignoring missing keys."""
    template = TEMPLATES[doc_type]
    try:
        return template.format(**inputs)
    except KeyError:
        result = template
        for k, v in inputs.items():
            result = result.replace("{" + k + "}", v)
        return result


def generate_with_groq(
    prompt: str,
    model: str = "llama-3.3-70b-versatile",
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> str:
    """Call Groq API and return the generated markdown.

    Automatically fetches up to 2 continuation chunks when the response is
    truncated by the token limit, so long documents (textbooks, curricula)
    are never silently cut off.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to your .env file and retry.")

    client = Groq(api_key=api_key)
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    def emit(event: str, **payload) -> None:
        if progress_callback:
            progress_callback({"event": event, **payload})

    def _call(label: str) -> tuple[str, str]:
        emit("llm_call_started", label=label)
        with Live(
            Spinner("dots", text=f"[cyan]{label}[/cyan]"),
            console=_console,
            refresh_per_second=12,
            transient=True,
        ):
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=8000,
            )
        usage = getattr(resp, "usage", None)
        emit(
            "llm_call_completed",
            label=label,
            finish_reason=resp.choices[0].finish_reason,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )
        return resp.choices[0].message.content, resp.choices[0].finish_reason

    print()
    emit("generation_started", model=model)
    content, finish_reason = _call("Generating content via Groq…")
    emit("chunk_completed", chunk_number=1, finish_reason=finish_reason)

    # Continuation loop — up to 2 extra chunks (handles ~24 K tokens total)
    chunk = 1
    while finish_reason == "length" and chunk < 3:
        _console.print(
            f"[yellow]⚠  Response was cut off — fetching continuation {chunk}/2…[/yellow]"
        )
        emit("continuation_requested", continuation_number=chunk)
        messages.append({"role": "assistant", "content": content})
        messages.append({
            "role": "user",
            "content": (
                "Continue the document exactly where it was cut off. "
                "Do not repeat any content already written. "
                "Resume mid-sentence if necessary."
            ),
        })
        continuation, finish_reason = _call(f"Continuation {chunk}/2…")
        content += "\n\n" + continuation
        messages.append({"role": "assistant", "content": continuation})
        emit("chunk_completed", chunk_number=chunk + 1, finish_reason=finish_reason)
        chunk += 1

    _console.print("[green]✓ Content generated[/green]")
    emit("generation_finished", total_chunks=chunk)
    return content


def save_markdown(content: str, doc_type: DocType, subject: str) -> Path:
    """Save generated content to a markdown file."""
    safe_name = subject.lower().replace(" ", "_")[:40]
    filename = f"{doc_type.value}_{safe_name}.md"
    filepath = OUTPUT_DIR / filename
    filepath.write_text(content, encoding="utf-8")
    return filepath


def run() -> Path:
    """Full interactive flow. Returns the path to the saved markdown file."""
    doc_type = pick_doc_type()
    curriculum = pick_curriculum()
    difficulty = pick_difficulty()
    inputs = collect_inputs(doc_type)
    inputs["curriculum"] = curriculum
    inputs["difficulty"] = difficulty
    prompt = build_prompt(doc_type, inputs)
    try:
        content = generate_with_groq(prompt)
    except ValueError as e:
        print(f"\n✗ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Groq API error: {e}")
        sys.exit(1)
    md_path = save_markdown(content, doc_type, inputs.get("subject", "document"))
    print(f"✓ Markdown saved → {md_path}")
    return md_path


if __name__ == "__main__":
    run()
