# Teaching Aid Generator

Generate polished teaching materials with AI, export them as Markdown and PDF, and work from a Studio-style Streamlit interface built for long-form academic content.

## What it does

- Generates textbooks, lesson plans, schemes of work, syllabi, assessment rubrics, and activity sheets
- Aligns output to curricula such as WAEC, NECO, JAMB, GCSE, AP, IB, and more
- Handles long responses with chunk continuation so large documents are less likely to be cut off
- Exports both editable Markdown and presentation-ready PDF files
- Detects image directives and either renders Google-generated illustrations or falls back to styled placeholders
- Includes a modern Streamlit "Studio" UI with blueprint controls, progress states, canvas preview, and activity log

## Studio UI

The web app in [app.py](app.py) is designed as an AI-native workspace rather than a basic form:

- Left blueprint panel for document setup
- Center canvas for generated content preview
- Top progress stepper for researching, drafting, and polishing
- Terminal-style activity log for generation events
- Quick actions for Markdown export, PDF download, and regeneration

Run it with:

```bash
streamlit run app.py
```

By default Streamlit opens at `http://localhost:8501`.

## Supported document types

- Textbook / Study Guide
- Scheme of Work
- Full Curriculum
- Lesson Plan
- Syllabus
- Assessment Rubric
- Classwork / Activity Sheet

## Requirements

- Python 3.10+
- A Groq API key for text generation
- Optional: a Google API key for image generation during PDF export

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment setup

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_your_actual_key_here
GEMINI_API_KEY=your_google_api_key_here
```

Notes:

- `GROQ_API_KEY` is required for content generation
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` is optional and enables real image generation during PDF export

## How to use

### Option 1: Streamlit Studio

```bash
streamlit run app.py
```

This is the recommended workflow if you want:

- a guided UI
- real-time generation feedback
- canvas preview
- one-click Markdown and PDF export

### Option 2: CLI workflow

```bash
python run.py
```

This interactive flow will:

1. ask for the document type
2. collect the needed fields
3. generate Markdown through Groq
4. save Markdown to `output/`
5. build a PDF from the generated Markdown

### Option 3: Convert existing Markdown to PDF

```bash
python run.py --pdf-only path/to/file.md
```

## Image generation

The content generator can insert directives like:

```text
[GENERATE IMAGE: A labeled diagram showing the water cycle]
```

During PDF generation the app will:

- detect image directives in the Markdown
- attempt Google image generation if an API key is configured
- embed generated images into the PDF when successful
- fall back to styled placeholders if generation fails or no key is set

This makes it safe to use the same content flow for both draft and production output.

## Long-form generation

For larger documents such as textbooks and curricula, the app automatically requests continuation chunks when the initial LLM response is truncated by token limits.

Current behavior:

- first response up to about 8,000 tokens
- up to 2 continuation fetches
- around 24,000 tokens total stitched together in one document

## Project structure

```text
TeachingAidGenerator/
|-- app.py
|-- config.py
|-- generate_content.py
|-- generate_pdf.py
|-- image_gen.py
|-- run.py
|-- requirements.txt
|-- output/
`-- README.md
```

## Core files

- [app.py](app.py): Streamlit Studio UI
- [config.py](config.py): document types, curricula, prompt templates, and field definitions
- [generate_content.py](generate_content.py): Groq prompting, continuation logic, and CLI data collection
- [generate_pdf.py](generate_pdf.py): Markdown parsing and PDF layout
- [image_gen.py](image_gen.py): image directive parsing and Google image generation helpers
- [run.py](run.py): end-to-end CLI entrypoint

## Output

Generated files are written to `output/`:

- `.md` for editable content
- `.pdf` for formatted delivery

## Typical instruction ideas

Use the instructions field to guide the generator with details like:

- Include Nigerian examples
- Align to WAEC syllabus
- Use British English spelling
- Add practical lab exercises
- Include exam tips per section
- Add 4 to 5 diagrams per chapter

## Known limitations

- Section-level regeneration is not implemented yet; regeneration currently reruns the document flow
- Real image generation depends on external API access and available credits
- Very long outputs can still need manual review and editing before final distribution

## Development notes

Quick syntax check:

```bash
python -m compileall app.py generate_content.py
```

If you want to improve the repo further, the next good steps would be:

- add screenshots of the Studio UI
- add tests for prompt-building and markdown parsing
- split the Streamlit UI into smaller reusable modules
