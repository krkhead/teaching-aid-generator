╔══════════════════════════════════════════════════════════════╗
║              TEACHING AID GENERATOR — Instructions           ║
╚══════════════════════════════════════════════════════════════╝

WHAT THIS DOES
──────────────
Generates professional teaching materials as PDFs using AI.
Supported document types:
  1. Textbook / Study Guide
  2. Scheme of Work
  3. Curriculum
  4. Lesson Plan
  5. Syllabus
  6. Assessment Rubric


REQUIREMENTS
────────────
- Python 3.10+
- Install all dependencies:
    pip install -r requirements.txt
- A Groq API key (free at https://console.groq.com)


SETUP
─────
1. Open the .env file in this folder
2. Add your Groq API key (required for content generation):
   GROQ_API_KEY=gsk_your_actual_key_here
3. (Optional) Add your Google API key for automatic image generation:
   GEMINI_API_KEY=your_google_api_key_here
4. Save the file


HOW TO RUN
──────────
Option A — Web UI (recommended):

  streamlit run app.py

  Opens a browser at http://localhost:8501 with a full form UI.
  Fill in the details, click Generate, then download your PDF or Markdown.

Option B — Command line:

  python run.py

  You will be prompted to:
  1. Choose a document type (textbook, curriculum, etc.)
  2. Enter details (subject, audience, level, duration, etc.)
  3. Wait while the AI generates content (animated spinner shown)
  4. A markdown file (.md) and PDF are saved to the output/ folder

Note: Long documents (textbooks, curricula) are automatically continued
if the AI hits the token limit — up to 3 chunks (~24 000 tokens) are
fetched and stitched together seamlessly.


CONVERT EXISTING MARKDOWN TO PDF
─────────────────────────────────
If you already have a markdown file and just want the PDF:

  python run.py --pdf-only path/to/your_file.md


OUTPUT
──────
All generated files go to the output/ folder:
  - .md file  = raw markdown (editable, re-run PDF anytime)
  - .pdf file = professional formatted document


IMAGE GENERATION
────────────────
The system automatically detects when the AI includes image generation
prompts and creates styled placeholders in the PDF.

How it works:
  1. AI generates markdown with [GENERATE IMAGE: description] directives
  2. PDF converter detects these and creates image placeholder boxes
  3. Placeholders show the image description for context
  4. You can later:
     - Manually generate images via AI and insert into PDF
     - Use the descriptions to commission illustrations
     - Leave as placeholders (useful for drafts)

To disable placeholders and use plain text instead:
  Edit config.py and set IMAGE_CONFIG["enabled"] = False

Real image generation
  The system now supports automatic image generation via Google Imagen 3:
  - Add your Google API key to .env as GEMINI_API_KEY or GOOGLE_API_KEY
  - The system automatically detects when the API key is set
  - Images are generated in real-time and embedded in the PDF
  - If generation fails for any image, the system falls back to a styled placeholder
  (Requires internet and uses Google API credits)

TIPS
────
- You can edit the .md file after generation, then re-run:
    python run.py --pdf-only output/your_file.md

- For longer documents (textbooks), the AI may hit token limits.
  If output is cut short, edit the .md file to add remaining
  chapters manually, then regenerate the PDF.

- The "Special instructions" field is powerful. Use it to specify
  things like:
    "Include Nigerian examples"
    "Align to WAEC syllabus"
    "Use British English spelling"
    "Add practical lab exercises"
    "Include exam tips per section"
    "Add 4-5 diagrams per chapter"


FILE STRUCTURE
──────────────
TeachingAidGenerator/
├── .env                  ← Your Groq API key (DO NOT SHARE)
├── config.py             ← Document types and prompt templates
├── generate_content.py   ← AI content generation (Groq)
├── generate_pdf.py       ← Markdown to PDF converter
├── run.py                ← Main script (run this)
├── output/               ← Generated files go here
└── README.txt            ← This file
