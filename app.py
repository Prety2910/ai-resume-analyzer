import os
import re
from datetime import datetime

import pdfplumber
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

JOB_ROLES = {
    "Python Developer": ["python", "flask", "django", "sql", "git", "api", "pandas", "numpy"],
    "Data Analyst": ["python", "sql", "excel", "pandas", "numpy", "tableau", "power bi", "statistics"],
    "Cloud Engineer": ["aws", "azure", "gcp", "linux", "docker", "kubernetes", "networking", "devops"],
    "Frontend Developer": ["html", "css", "javascript", "react", "bootstrap", "ui", "responsive", "git"],
    "Java Developer": ["java", "spring", "hibernate", "sql", "oop", "git", "api"],
}

MASTER_SKILLS = sorted(
    set(skill for role in JOB_ROLES.values() for skill in role).union(
        {
            "c", "c++", "firebase", "mongodb", "mysql", "postgresql",
            "node.js", "express", "github", "machine learning",
            "data structures", "algorithms", "communication", "problem solving"
        }
    )
)

LATEST_ANALYSIS = {}


def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text_from_pdf(pdf_path: str) -> str:
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    return "\n".join(text).strip()


def extract_skills(resume_text: str) -> list[str]:
    text = clean_text(resume_text)
    found = []

    for skill in MASTER_SKILLS:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text):
            found.append(skill)

    return sorted(found, key=str.lower)


def calculate_role_matches(resume_text: str) -> dict:
    resume_text = clean_text(resume_text)
    scores = {}

    for role, skills in JOB_ROLES.items():
        role_text = " ".join(skills)
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform([resume_text, role_text])
        similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        scores[role] = round(similarity * 100, 1)

    return dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))


def get_missing_skills(best_role: str, detected_skills: list[str]) -> list[str]:
    required = JOB_ROLES.get(best_role, [])
    detected_lower = {s.lower() for s in detected_skills}
    return [skill for skill in required if skill.lower() not in detected_lower]


def calculate_score(resume_text: str, detected_skills: list[str], best_role: str) -> int:
    text = clean_text(resume_text)
    words = text.split()
    word_count = len(words)
    score = 0

    if word_count >= 400:
        score += 20
    elif word_count >= 250:
        score += 15
    elif word_count >= 150:
        score += 10
    else:
        score += 5

    sections = ["education", "skills", "projects", "project", "experience", "internship", "certification"]
    section_count = sum(1 for section in sections if section in text)
    score += min(section_count * 5, 20)

    score += min(len(detected_skills) * 2, 20)

    required = JOB_ROLES.get(best_role, [])
    if required:
        matched = sum(1 for skill in required if skill.lower() in {s.lower() for s in detected_skills})
        coverage = int((matched / len(required)) * 30)
        score += coverage

    if re.search(r"\b(built|developed|implemented|designed|improved|created|achieved|led)\b", text):
        score += 10

    return min(score, 100)


def get_score_label(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 65:
        return "Good"
    if score >= 50:
        return "Average"
    return "Needs Improvement"


def get_suggestions(resume_text: str, detected_skills: list[str], best_role: str, score: int) -> list[str]:
    text = clean_text(resume_text)
    suggestions = []

    if len(text.split()) < 250:
        suggestions.append("Add a little more relevant content such as projects, internships, and technical achievements.")

    if "skills" not in text:
        suggestions.append("Add a dedicated Technical Skills section.")

    if "project" not in text and "projects" not in text:
        suggestions.append("Add a Projects section to improve your ATS relevance.")

    if "experience" not in text and "internship" not in text:
        suggestions.append("Add internship, volunteer, or practical experience if available.")

    if not re.search(r"\b(built|developed|implemented|designed|improved|created|achieved|led)\b", text):
        suggestions.append("Use more action verbs like built, developed, implemented, and improved.")

    missing = get_missing_skills(best_role, detected_skills)
    if missing:
        suggestions.append(f"For {best_role}, try adding these skills if relevant: {', '.join(missing[:5])}.")

    if "summary" not in text and "objective" not in text:
        suggestions.append("Add a short professional summary at the top of your resume.")

    if score < 60:
        suggestions.append("Tailor your resume more closely to the target role using role-specific keywords.")

    return suggestions[:6]


def chatbot_reply(message: str, analysis: dict) -> str:
    q = message.lower().strip()

    score = analysis.get("score", 0)
    best_role = analysis.get("best_role", "Unknown")
    word_count = analysis.get("word_count", 0)
    detected_skills = analysis.get("detected_skills", [])
    missing_skills = analysis.get("missing_skills", [])
    suggestions = analysis.get("suggestions", [])

    if "improve" in q or "better" in q:
        if suggestions:
            return "Here are the main improvements: " + " ".join(
                f"{i+1}. {tip}" for i, tip in enumerate(suggestions[:4])
            )
        return "Your resume is already decent. Focus on adding stronger projects, achievements, and role-specific keywords."

    if "missing" in q or "skills" in q:
        if missing_skills:
            return f"For {best_role}, the missing or weaker skills are: {', '.join(missing_skills)}."
        return f"You already cover most important skills for {best_role}."

    if "best role" in q or "job role" in q or "suits me" in q:
        return f"Your best matched role is {best_role}."

    if "score" in q or "ats" in q:
        return f"Your ATS score is {score}%. Improving keywords, sections, and achievements can raise it."

    if "word" in q or "length" in q:
        return f"Your resume has around {word_count} words."

    if "summary" in q:
        top_skills = ", ".join(detected_skills[:5]) if detected_skills else "software development"
        return (
            f"You can use this summary: "
            f"'Motivated candidate with skills in {top_skills}, seeking opportunities as a {best_role} "
            f"to apply technical knowledge and problem-solving abilities.'"
        )

    if "hi" in q or "hello" in q:
        return "Hi. Ask me about your ATS score, best role, missing skills, summary, or how to improve your resume."

    return "I can help with your ATS score, best role, missing skills, resume improvements, and summary suggestion."


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["resume"]

    if not file or file.filename == "":
        return jsonify({"error": "Please choose a PDF file."}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    try:
        resume_text = extract_text_from_pdf(file_path)

        if not resume_text.strip():
            return jsonify({"error": "Could not extract text from this PDF."}), 400

        detected_skills = extract_skills(resume_text)
        role_matches = calculate_role_matches(resume_text)
        best_role = next(iter(role_matches)) if role_matches else "Unknown"
        score = calculate_score(resume_text, detected_skills, best_role)
        missing_skills = get_missing_skills(best_role, detected_skills)
        suggestions = get_suggestions(resume_text, detected_skills, best_role, score)
        word_count = len(clean_text(resume_text).split())
        score_label = get_score_label(score)

        analysis = {
            "score": score,
            "score_label": score_label,
            "word_count": word_count,
            "best_role": best_role,
            "best_match_score": role_matches.get(best_role, 0),
            "all_job_matches": role_matches,
            "detected_skills": detected_skills,
            "missing_skills": missing_skills,
            "suggestions": suggestions,
            "file_name": file.filename,
            "analyzed_at": datetime.now().strftime("%d-%m-%Y %I:%M %p"),
        }

        global LATEST_ANALYSIS
        LATEST_ANALYSIS = analysis

        return jsonify(analysis)

    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    analysis = data.get("analysis") or LATEST_ANALYSIS

    if not message:
        return jsonify({"reply": "Please type a question first."}), 400

    if not analysis:
        return jsonify({"reply": "Please analyze a resume first."})

    return jsonify({"reply": chatbot_reply(message, analysis)})


if __name__ == "__main__":
    app.run(debug=True)
