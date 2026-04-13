"""Image generation and placeholder handling for PDFs.

Detects [GENERATE IMAGE: description] directives in markdown.
Generates images via Google Gemini API or creates placeholder boxes.
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Spacer, Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle


# ── Image directive parsing ─────────────────────────────────────────────────

def extract_image_directives(markdown_text: str) -> list[tuple[str, int]]:
    """Extract all [GENERATE IMAGE: description] directives from markdown.

    Returns list of (description, line_number) tuples.
    """
    directives = []
    for i, line in enumerate(markdown_text.splitlines(), 1):
        m = re.search(r"\[GENERATE IMAGE:\s*(.+?)\]", line)
        if m:
            description = m.group(1).strip()
            directives.append((description, i))
    return directives


def clean_image_directives(markdown_text: str) -> str:
    """Remove [GENERATE IMAGE: ...] directives from markdown, replace with placeholders."""
    def replacer(match):
        desc = match.group(1).strip()
        return f"[Image: {desc}]"

    return re.sub(r"\[GENERATE IMAGE:\s*(.+?)\]", replacer, markdown_text)


# ── PDF placeholder rendering ───────────────────────────────────────────────

def create_image_placeholder(
    description: str,
    width: float = 12 * cm,
    height: float = 8 * cm,
) -> Table:
    """Create a styled placeholder box for a missing/pending image in PDF.

    Args:
        description: Image description text
        width: Placeholder width in cm
        height: Placeholder height in cm

    Returns:
        ReportLab Table with styled placeholder
    """
    # Truncate description if too long
    if len(description) > 100:
        description = description[:97] + "..."

    # Create text for the placeholder
    style = ParagraphStyle(
        "PlaceholderText",
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=colors.HexColor("#8899a6"),
        alignment=1,  # center
        wordWrap="CJK",
    )

    text = Paragraph(f"<b>[Image placeholder]</b><br/><br/><i>{description}</i>", style)

    # Create table with placeholder styling
    t = Table([[text]], colWidths=[width], rowHeights=[height])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f3f6")),
        ("BORDER", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    return t


# ── Real image generation (optional) ────────────────────────────────────────

async def generate_image_stability_ai(
    description: str,
    api_key: Optional[str] = None,
) -> Optional[bytes]:
    """Generate image via Stability AI API (requires paid account).

    Args:
        description: Image description
        api_key: Stability AI API key (reads from STABILITY_AI_API_KEY env if not provided)

    Returns:
        Image bytes if successful, None if failed or API key not available
    """
    api_key = api_key or os.environ.get("STABILITY_AI_API_KEY")
    if not api_key:
        return None

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.stability.ai/v1/generate/stable-image/generate",
                headers={
                    "authorization": f"Bearer {api_key}",
                    "accept": "image/*",
                },
                data={"prompt": description, "output_format": "png"},
                timeout=60.0,
            )
            if response.status_code == 200:
                return response.content
    except Exception as e:
        print(f"[!] Image generation failed for '{description[:50]}...': {e}")

    return None


def generate_image_gemini(
    description: str,
    api_key: Optional[str] = None,
) -> Optional[bytes]:
    """Generate image via Google Gemini 2.0 Flash (native image generation).

    Uses the new google.genai SDK with Gemini 2.0 Flash's multimodal output.

    Args:
        description: Image description
        api_key: Google API key (reads from GEMINI_API_KEY or GOOGLE_API_KEY env if not provided)

    Returns:
        Image bytes (PNG) if successful, None if failed
    """
    api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=f"Generate an educational illustration: {description}. "
                     f"Make it clear, professional, suitable for a textbook. "
                     f"Use clean lines and labels where appropriate.",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # Extract image from response parts
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    return part.inline_data.data

    except Exception as e:
        print(f"[!] Gemini image generation failed for '{description[:50]}...': {e}")

    return None


# ── Integration helper ──────────────────────────────────────────────────────

def should_generate_real_images() -> bool:
    """Check if real image generation is configured.

    Returns True if GEMINI_API_KEY or GOOGLE_API_KEY is set.
    """
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
