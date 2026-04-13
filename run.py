"""Teaching Aid Generator — end-to-end orchestrator.

Run this script to:
1. Pick a document type (textbook, curriculum, scheme of work, etc.)
2. Fill in the details interactively
3. Generate content via Groq LLM
4. Convert to a professional PDF

Usage:
    python run.py                  # Full interactive flow
    python run.py --pdf-only FILE  # Convert an existing markdown file to PDF
"""

import argparse
import sys
from pathlib import Path

from config import DOC_LABELS, DocType
from generate_content import run as generate_markdown
from generate_pdf import build_pdf


def full_flow():
    """Interactive: generate markdown then convert to PDF."""
    md_path = generate_markdown()

    # Determine doc type from filename for the cover label
    label = "Professional Teaching Aid"
    for dt in DocType:
        if md_path.stem.startswith(dt.value):
            label = DOC_LABELS[dt]
            break

    pdf_path = md_path.with_suffix(".pdf")
    try:
        build_pdf(md_path, pdf_path, doc_type_label=label)
    except Exception as e:
        print(f"\n✗ PDF generation failed: {e}")
        print(f"  Your markdown is still saved at: {md_path}")
        print("  Fix the issue and retry with: python run.py --pdf-only " + str(md_path))
        sys.exit(1)
    print(f"✓ PDF generated → {pdf_path}")
    print(f"\nDone! Your files are in: {md_path.parent}")


def pdf_only(md_file: str):
    """Convert an existing markdown file to PDF."""
    md_path = Path(md_file)
    if not md_path.exists():
        print(f"✗ File not found: {md_path}")
        sys.exit(1)
    pdf_path = md_path.with_suffix(".pdf")
    try:
        build_pdf(md_path, pdf_path)
    except Exception as e:
        print(f"\n✗ PDF generation failed: {e}")
        sys.exit(1)
    print(f"✓ PDF generated → {pdf_path}")


def main():
    parser = argparse.ArgumentParser(description="Teaching Aid Generator")
    parser.add_argument(
        "--pdf-only",
        metavar="FILE",
        help="Skip generation — just convert an existing .md file to PDF",
    )
    args = parser.parse_args()

    if args.pdf_only:
        pdf_only(args.pdf_only)
    else:
        full_flow()


if __name__ == "__main__":
    main()
