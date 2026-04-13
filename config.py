"""Document type definitions and prompt templates for teaching aid generation."""

from enum import Enum


class DocType(Enum):
    TEXTBOOK = "textbook"
    SCHEME_OF_WORK = "scheme_of_work"
    CURRICULUM = "curriculum"
    LESSON_PLAN = "lesson_plan"
    SYLLABUS = "syllabus"
    ASSESSMENT_RUBRIC = "assessment_rubric"
    ACTIVITY_SHEET = "activity_sheet"


DOC_LABELS = {
    DocType.TEXTBOOK: "Textbook / Study Guide",
    DocType.SCHEME_OF_WORK: "Scheme of Work",
    DocType.CURRICULUM: "Full Curriculum",
    DocType.LESSON_PLAN: "Lesson Plan",
    DocType.SYLLABUS: "Syllabus",
    DocType.ASSESSMENT_RUBRIC: "Assessment Rubric",
    DocType.ACTIVITY_SHEET: "Classwork / Activity Sheet",
}

# ── Examining bodies / curricula ────────────────────────────────────────────

CURRICULA = {
    # Nigeria
    "1": ("WAEC", "WAEC (West African Examinations Council) — Nigeria / West Africa"),
    "2": ("NECO", "NECO (National Examinations Council) — Nigeria"),
    "3": ("JAMB", "JAMB (Joint Admissions and Matriculation Board) — Nigeria"),
    # UK
    "4": ("GCSE", "GCSE — United Kingdom"),
    "5": ("A-Level", "A-Level — United Kingdom"),
    "6": ("Cambridge IGCSE", "Cambridge IGCSE — International"),
    # US
    "7": ("AP", "AP (Advanced Placement) — United States"),
    "8": ("SAT", "SAT — United States"),
    "9": ("Common Core", "Common Core State Standards — United States"),
    # International
    "10": ("IB", "IB (International Baccalaureate) — International"),
    "11": ("Cambridge A-Level", "Cambridge International A-Level"),
    "12": ("Edexcel", "Edexcel (Pearson) — International"),
    # Professional / Other
    "13": ("CompTIA", "CompTIA Certifications (Security+, Network+, etc.)"),
    "14": ("Cisco", "Cisco Certifications (CCNA, CCNP, etc.)"),
    "15": ("Custom", "Custom / Other (specify in instructions)"),
}

# ── Difficulty levels ───────────────────────────────────────────────────────

DIFFICULTIES = {
    "1": "Beginner",
    "2": "Intermediate",
    "3": "Advanced",
}

# ── Image generation settings ────────────────────────────────────────────────

IMAGE_CONFIG = {
    "enabled": True,  # Set to False to skip image generation, use placeholders only
    "max_images_per_section": 2,  # Limit images per major section
    "image_width": 600,  # pixels
    "image_height": 400,  # pixels
    "fallback_to_placeholder": True,  # If image gen fails, show text placeholder
}

# ── Prompt templates per document type ──────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a veteran curriculum developer with 20 years of experience writing "
    "published textbooks, government-approved schemes of work, and training manuals "
    "for examining bodies worldwide. You write like a human subject-matter expert, "
    "not like an AI.\n\n"

    "WRITING RULES — follow these strictly:\n"
    "- Write in a direct, confident, professional voice. No hedging, no filler.\n"
    "- NEVER use these phrases: 'In this section', 'It is important to note', "
    "'This ensures that', 'By the end of this', 'In today's world', "
    "'It is worth noting', 'Furthermore', 'Moreover', 'In conclusion', "
    "'Let's delve into', 'students will be able to', 'This comprehensive'.\n"
    "- Do NOT start every section the same way. Vary your openings.\n"
    "- Do NOT repeat the same assessment method for every single week/unit. "
    "Use a realistic mix: oral questioning, written exercises, peer review, "
    "group presentations, practical tasks, quizzes, project work, portfolios.\n"
    "- Do NOT use generic filler resources like 'whiteboard, markers, calculators' "
    "for every section. Name specific textbooks, chapters, past exam papers, "
    "software tools, or real-world materials relevant to the topic.\n"
    "- Each section must feel distinct — different structure, different depth, "
    "different activities. A real teacher would not copy-paste the same template "
    "12 times with different topic names.\n"
    "- Use concrete examples, specific page references, named exam paper years, "
    "and real teaching strategies.\n\n"

    "FORMAT RULES:\n"
    "- Use markdown: # for document title, ## for major sections, ### for subsections, "
    "- for bullet points, and plain paragraphs for body text.\n"
    "- Do NOT use bold (**) in headings — the heading level provides emphasis.\n"
    "- For structured fields within a section (e.g. Topic, Duration, Resources), "
    "write them as 'Label: Value' on their own line — one per line.\n"
    "- Output ONLY the markdown content. No preamble, no sign-off, no commentary.\n\n"

    "ALIGNMENT RULE:\n"
    "Strictly align all content — topics, sequencing, depth, terminology, "
    "and exam focus — to the specified examining body and class level. "
    "Reference the official syllabus structure where applicable. "
    "If the examining body publishes topic codes or objective numbers, use them.\n\n"

    "IMAGE GENERATION DIRECTIVE:\n"
    "At strategic points, insert image generation prompts using this syntax:\n"
    "[GENERATE IMAGE: detailed visual description]\n"
    "Example: [GENERATE IMAGE: A diagram showing the water cycle with evaporation, "
    "condensation, and precipitation clearly labeled with arrows]\n"
    "Include 1-3 images per major section where a visual aid significantly enhances understanding. "
    "Create diagrams, flowcharts, timelines, concept maps, or annotated illustrations. "
    "The system will automatically generate these images and embed them in the PDF."
)

TEMPLATES: dict[DocType, str] = {
    DocType.TEXTBOOK: (
        "Write a textbook / study guide.\n\n"
        "Subject: {subject}\n"
        "Class: {class_level}\n"
        "Curriculum: {curriculum}\n"
        "Difficulty: {difficulty}\n"
        "Chapters: {units}\n"
        "Instructions: {instructions}\n\n"
        "Align to the {curriculum} syllabus for {class_level} {subject}.\n\n"
        "For each chapter, provide:\n"
        "### Chapter title\n"
        "- 3-5 specific learning outcomes (not generic 'understand X' statements)\n"
        "- Substantive explanatory content with worked examples drawn from "
        "past {curriculum} exam questions where possible\n"
        "- Key terms defined in context, not as a detached glossary\n"
        "- 5-8 review questions that mirror actual {curriculum} exam style and difficulty\n"
        "- A concise chapter summary\n\n"
        "Make each chapter genuinely different in structure and approach. "
        "A chapter on practical skills should read differently from a chapter on theory."
    ),
    DocType.SCHEME_OF_WORK: (
        "Write a scheme of work.\n\n"
        "Subject: {subject}\n"
        "Class: {class_level}\n"
        "Curriculum: {curriculum}\n"
        "Difficulty: {difficulty}\n"
        "Duration: {duration}\n"
        "Hours per week: {hours_per_week}\n"
        "Instructions: {instructions}\n\n"
        "Align to the {curriculum} syllabus for {class_level} {subject}.\n\n"
        "Use ## for each week. Within each week, structure as:\n"
        "Topic: [the topic]\n"
        "Subtopics: [specific subtopics from the {curriculum} syllabus]\n"
        "Learning outcomes: [2-4 specific, measurable outcomes]\n"
        "Teaching strategy: [describe the actual pedagogical approach — not just "
        "'teacher explains'. Include group work, demonstrations, problem-solving "
        "sessions, past-paper drills, peer teaching, etc. Vary across weeks.]\n"
        "Resources: [name specific textbooks with chapters, past paper years, "
        "lab equipment, software, online tools — not 'whiteboard and markers']\n"
        "Assessment: [vary across weeks — classwork, homework, oral quiz, "
        "group presentation, mini-project, timed test, peer marking, etc.]\n\n"
        "Each week must feel like a distinct plan a real teacher wrote, "
        "not a template with swapped-out topic names."
    ),
    DocType.CURRICULUM: (
        "Write a full training curriculum.\n\n"
        "Subject: {subject}\n"
        "Class: {class_level}\n"
        "Curriculum: {curriculum}\n"
        "Difficulty: {difficulty}\n"
        "Duration: {duration}\n"
        "Hours per week: {hours_per_week}\n"
        "Instructions: {instructions}\n\n"
        "Align to the {curriculum} syllabus and examination structure.\n\n"
        "Include these sections (each as a ## heading):\n"
        "1. Programme overview — purpose, scope, and intended outcomes\n"
        "2. Examination alignment — map to {curriculum} domains/papers with weightings\n"
        "3. Delivery model — duration, weekly hours, format, prerequisite knowledge\n"
        "4. Learner profile — who this is for, expected entry level\n"
        "5. Instructional approach — teaching philosophy and methods\n"
        "6. Module breakdown — each module with topics, hours allocated, and "
        "percentage of overall programme\n"
        "7. Weekly scheme of work — condensed week-by-week plan\n"
        "8. Assessment strategy — formative and summative methods, grading criteria\n"
        "9. Recommended resources — specific textbooks, past papers, digital tools\n"
        "10. Quality assurance — how the programme tracks learner progress"
    ),
    DocType.LESSON_PLAN: (
        "Write a lesson plan.\n\n"
        "Subject: {subject}\n"
        "Topic: {topic}\n"
        "Class: {class_level}\n"
        "Curriculum: {curriculum}\n"
        "Difficulty: {difficulty}\n"
        "Duration: {duration}\n"
        "Instructions: {instructions}\n\n"
        "Align to the {curriculum} syllabus for this topic.\n\n"
        "Structure:\n"
        "### Lesson overview\n"
        "Topic, class, duration, prior knowledge required, resources/materials.\n\n"
        "### Learning outcomes\n"
        "3-5 specific, assessable outcomes.\n\n"
        "### Lesson stages\n"
        "Break into timed stages with the actual teacher actions and student activities:\n"
        "- Introduction (hook / recall) — X minutes\n"
        "- Development (new content) — X minutes\n"
        "- Guided practice — X minutes\n"
        "- Independent practice — X minutes\n"
        "- Plenary / assessment — X minutes\n\n"
        "### Differentiation\n"
        "How to support struggling learners and extend stronger ones.\n\n"
        "### Homework / follow-up\n"
        "Specific task with expected time to complete."
    ),
    DocType.SYLLABUS: (
        "Write a course syllabus.\n\n"
        "Subject: {subject}\n"
        "Class: {class_level}\n"
        "Curriculum: {curriculum}\n"
        "Difficulty: {difficulty}\n"
        "Duration: {duration}\n"
        "Instructions: {instructions}\n\n"
        "Align to the {curriculum} syllabus and exam objectives.\n\n"
        "Include:\n"
        "- Course title and description\n"
        "- Prerequisites\n"
        "- Learning outcomes mapped to {curriculum} objectives\n"
        "- Week-by-week topic outline with specific readings\n"
        "- Assessment breakdown with dates/weights\n"
        "- Grading scale\n"
        "- Course policies (attendance, late work, academic integrity)\n"
        "- Required and recommended materials (specific editions)"
    ),
    DocType.ASSESSMENT_RUBRIC: (
        "Write an assessment rubric.\n\n"
        "Subject: {subject}\n"
        "Assessment type: {topic}\n"
        "Class: {class_level}\n"
        "Curriculum: {curriculum}\n"
        "Difficulty: {difficulty}\n"
        "Instructions: {instructions}\n\n"
        "Align to {curriculum} grading standards.\n\n"
        "Include:\n"
        "- Rubric title and purpose\n"
        "- At least 5 assessment criteria, each as a ### subsection\n"
        "- For each criterion: description, then four performance levels "
        "(Excellent / Good / Satisfactory / Needs Improvement) with "
        "specific, distinguishing descriptors — not vague rewordings of each other\n"
        "- Scoring weights per criterion\n"
        "- Total marks and grade boundaries"
    ),
    DocType.ACTIVITY_SHEET: (
        "Write a classwork / activity sheet for students to complete in class.\n\n"
        "Subject: {subject}\n"
        "Topic: {topic}\n"
        "Class: {class_level}\n"
        "Curriculum: {curriculum}\n"
        "Difficulty: {difficulty}\n"
        "Duration: {duration}\n"
        "Number of questions/activities: {num_activities}\n"
        "Instructions: {instructions}\n\n"
        "Align every question and activity to the {curriculum} syllabus for {class_level} {subject}.\n\n"
        "SHEET STRUCTURE:\n\n"
        "Start with a header block using 'Label: Value' lines:\n"
        "Name:\n"
        "Class:\n"
        "Date:\n"
        "Time Allowed: {duration}\n"
        "Total Marks: [calculate from sections below]\n\n"
        "Then include these sections as ## headings:\n\n"
        "## Section A — Recall & Warm-Up\n"
        "4-6 short-answer or fill-in-the-blank questions on prerequisite knowledge. "
        "Each question worth 1-2 marks. These should take 5-8 minutes.\n\n"
        "## Section B — Core Activities\n"
        "The main body of the sheet. Use a MIX of at least 3 question types from: "
        "structured questions, calculations with working space, label-the-diagram, "
        "match-the-column, true/false with justification, data interpretation, "
        "short-paragraph response, or sequencing tasks. "
        "Distribute marks clearly. Each question should have [X marks] shown. "
        "Leave realistic working space after calculation questions.\n\n"
        "## Section C — Challenge / Extension\n"
        "1-2 higher-order questions: application, analysis, or problem-solving. "
        "These should stretch stronger students. Mark scheme hint in brackets.\n\n"
        "## Teacher's Answer Key\n"
        "Complete model answers for every question. For calculations, show full working. "
        "For open-ended questions, list 2-3 acceptable points. "
        "Mark this section clearly: 'TEACHER COPY — Do not distribute to students.'\n\n"
        "QUESTION WRITING RULES:\n"
        "- Number every question clearly (1, 2, 3... or A1, A2, B1, B2...)\n"
        "- Write questions that match actual {curriculum} exam style and command words "
        "(State, Calculate, Explain, Deduce, Compare, etc.)\n"
        "- Use realistic data, values, and contexts — not generic placeholders\n"
        "- Do NOT make all questions the same format or difficulty\n"
        "- Leave blank lines / boxes after questions where students need to write or draw"
    ),
}

# Fields required per doc type (beyond the universal ones)
EXTRA_FIELDS: dict[DocType, list[str]] = {
    DocType.TEXTBOOK: ["units"],
    DocType.SCHEME_OF_WORK: ["duration", "hours_per_week"],
    DocType.CURRICULUM: ["duration", "hours_per_week"],
    DocType.LESSON_PLAN: ["topic", "duration"],
    DocType.SYLLABUS: ["duration"],
    DocType.ASSESSMENT_RUBRIC: ["topic"],
    DocType.ACTIVITY_SHEET: ["topic", "duration", "num_activities"],
}

FIELD_PROMPTS: dict[str, str] = {
    "subject": "Subject / course name",
    "class_level": "Class / year group (e.g. 'SS2', 'Year 10', 'Grade 11', '100-Level')",
    "units": "Number of chapters / units (e.g. 10)",
    "num_activities": "Number of questions / activities (e.g. 15)",
    "duration": "Time allowed / duration (e.g. '45 minutes', '12 weeks')",
    "hours_per_week": "Hours per week (e.g. 5)",
    "topic": "Topic / subtopic",
    "instructions": "Any special instructions (press Enter to skip)",
}
