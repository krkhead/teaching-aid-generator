"""Generate TRCN PQE practice paper and PDF — v2 (improved variety + accuracy flags)."""
import os
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")
client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM = (
    "You are a veteran Nigerian examination item writer with 15 years of experience "
    "writing questions for TRCN (Teachers Registration Council of Nigeria) "
    "Professional Qualifying Examinations. "
    "You write realistic MCQ questions that match the exact style and difficulty of the TRCN PQE. "
    "Output ONLY structured markdown. No preamble, no commentary. "
    "Write like a human exam developer, not an AI. "
    "CRITICAL: Every question must be UNIQUE. Never repeat the same scenario, numbers, or structure. "
    "Vary your question stems heavily — no more than 2 questions can start with the same word."
)

PROMPT_A = """Write exactly 20 Use of English questions for a TRCN PQE practice paper. Number them 1 to 20.

STRICT VARIETY RULES — each of these question types must appear at least once:
- Subject-verb concord (at least 3 questions with different structures: collective noun, indefinite pronoun, compound subject)
- Tense usage (at least 2 — one past perfect, one future perfect continuous — using DIFFERENT contexts)
- Vocabulary/synonyms (at least 2 — use DIFFERENT words, not synonyms of each other)
- Figures of speech — at least 2, DIFFERENT devices (metaphor, simile, personification, hyperbole, oxymoron, irony — pick different ones per question)
- Comprehension/inference (1 short passage of 4–5 lines, followed by 2 questions about it)
- Oral English — stress and intonation (2 questions — one on word stress pattern, one on sentence stress)
- Parts of speech / sentence structure (1 question on identifying clauses or sentence type)
- Idiomatic expressions (1 question — different idiom from common ones)
- Antonyms (1 question)
- Direct/indirect speech (1 question)

Each question:
**[number]. [Stem — vary the opener: some start with a quoted sentence, some with "Which of the following...", some with "Choose the word...", some with "Identify the..."...]**
A) option  B) option  C) option  D) option

Do NOT number options on separate lines — keep A) B) C) D) on the same line or each on its own line consistently.
All 20 questions must be clearly different from each other in topic and structure."""

PROMPT_B = """Write exactly 20 Mathematics questions for a TRCN PQE practice paper. Number them 21 to 40.

STRICT VARIETY RULES — every question must use a DIFFERENT scenario and DIFFERENT numbers. Do NOT repeat the same setup.
Cover exactly these topics, one or two questions per topic:
- Q21–22: Number systems (LCM, HCF, or prime factorisation)
- Q23–24: Fractions and mixed numbers (addition/subtraction of unlike fractions, or conversion)
- Q25–26: Percentages (percentage increase/decrease — use real Nigerian classroom context like test scores or school fees)
- Q27–28: Ratio and proportion (sharing in a given ratio; unitary method)
- Q29–30: Simple algebra (solving for x in a linear equation; word problem involving unknowns)
- Q31–32: Geometry (angles in a triangle or polygon; properties of parallel lines)
- Q33–34: Area and perimeter (one question on circle, one on triangle — DIFFERENT dimensions from previous)
- Q35–36: Statistics (calculate the mean of a data set; identify the mode from a frequency table)
- Q37–38: Speed, distance, time (one question on time, one on distance — DIFFERENT contexts, not both cars)
- Q39–40: Profit and loss / simple interest (one on profit/loss percentage, one on simple interest formula)

Each question:
**[number]. [Clear problem statement with specific numbers]**
A) option  B) option  C) option  D) option

Distractors should be common calculation errors (wrong formula, arithmetic slip), not random numbers.
Show the correct working in a comment bracket after each question like this: {Working: ...}"""

PROMPT_C = """Write exactly 20 General Studies questions for a TRCN PQE practice paper. Number them 41 to 60.

Cover these areas with the exact distribution shown. Do NOT cluster all questions on one theorist or topic:
- Q41–43: Philosophy of Education (Q41: aims of education; Q42: a specific philosopher's view — Dewey, Rousseau, or Plato — name one per question; Q43: pragmatism vs idealism vs realism)
- Q44–46: Psychology of Education (Q44: Piaget's stages — name a specific stage and its age range; Q45: Vygotsky's ZPD concept; Q46: Bloom's Taxonomy — specific cognitive level)
- Q47–48: Sociology of Education (Q47: functions of education in society; Q48: concept of equality of educational opportunity in Nigeria)
- Q49–51: Curriculum Studies (Q49: Tyler's four fundamental questions; Q50: types of curriculum — hidden/null/overt; Q51: stages of curriculum development)
- Q52–54: Measurement and Evaluation (Q52: difference between measurement and evaluation; Q53: norm-referenced vs criterion-referenced assessment — a scenario-based question; Q54: purpose of continuous assessment under Nigeria's NERDC framework)
- Q55–57: Educational Management (Q55: functions of a school principal; Q56: what SBMC stands for and its primary function; Q57: a question on school records — which register records what)
- Q58: Teaching Methods (a scenario: "A teacher asks students to discover the rule themselves..." — which method is this?)
- Q59: Professional Ethics (a scenario involving TRCN Code of Conduct — what should the teacher do?)
- Q60: Nigerian Education System (UBE Act 2004 — what compulsory and free education range does it cover?)

ACCURACY FLAGS: For any answer you are less than 90% confident about, add [⚠️ Verify] at the end of the correct answer line.

Each question:
**[number]. [Stem]**
A) option  B) option  C) option  D) option"""

PROMPT_ANSWERKEY = """Write the Answer Key and Rationales for a 60-question TRCN practice paper.

The questions cover:
- Q1–20: Use of English (concord, tenses, vocabulary, figures of speech, comprehension, oral English, idioms)
- Q21–40: Mathematics (LCM/HCF, fractions, percentages, ratio, algebra, geometry, area, statistics, speed, profit/interest)
- Q41–60: General Studies (philosophy of education, educational psychology, sociology, curriculum studies, measurement & evaluation, educational management, teaching methods, professional ethics, UBE Act)

## ANSWER KEY

List correct answers in this grid format (10 per line):
1–10:
11–20:
21–30:
31–40:
41–50:
51–60:

## Selected Rationales

Write 18 rationales — 6 per section. For each:
**Q[number] — [topic tag]**
Correct: [letter]) [explanation of WHY this is correct — 2 sentences minimum]
Common distractor: [letter]) [why students pick this wrong answer and why it's incorrect]

Make rationales genuinely instructive, not just restating the answer."""


def call_groq(prompt, max_tokens=4000):
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        max_tokens=max_tokens,
    )
    content = resp.choices[0].message.content
    finish = resp.choices[0].finish_reason
    print(f"  chars={len(content)}, finish={finish}")
    return content


def main():
    print("Generating Section A — Use of English...")
    sec_a = call_groq(PROMPT_A, max_tokens=3500)

    print("Generating Section B — Mathematics...")
    sec_b = call_groq(PROMPT_B, max_tokens=3500)

    print("Generating Section C — General Studies...")
    sec_c = call_groq(PROMPT_C, max_tokens=3000)

    print("Generating Answer Key & Rationales...")
    key = call_groq(PROMPT_ANSWERKEY, max_tokens=3000)

    header = """# TRCN Professional Qualifying Examination — Practice Paper (v2)
## Use of English · Mathematics · General Studies

Name:
School/Institution:
Date:
Time Allowed: 2 hours
Total Marks: 60 (1 mark per question)
Instructions: Choose the most correct answer for each question. Each question carries 1 mark. No negative marking. Attempt ALL questions.

> *Note: Questions marked ⚠️ Verify should be cross-checked against the current official TRCN syllabus before use.*

---
"""

    full_content = (
        header
        + "\n## SECTION A — Use of English (Questions 1–20)\n\n"
        + sec_a
        + "\n\n---\n\n## SECTION B — Mathematics (Questions 21–40)\n\n"
        + sec_b
        + "\n\n---\n\n## SECTION C — General Studies (Questions 41–60)\n\n"
        + sec_c
        + "\n\n---\n\n"
        + key
    )

    out_md = Path(__file__).resolve().parent / "output" / "trcn_practice_paper_v2.md"
    out_md.write_text(full_content, encoding="utf-8")
    print(f"Markdown saved -> {out_md}")

    from generate_pdf import build_pdf
    out_pdf = out_md.with_suffix(".pdf")
    build_pdf(out_md, out_pdf, doc_type_label="TRCN PQE — Practice Paper v2")
    print(f"PDF saved -> {out_pdf}")


if __name__ == "__main__":
    main()
