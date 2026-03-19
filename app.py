"""
LectureChor — AI Note Taker
You skip class. We take notes.
Built with Streamlit + Whisper + Claude
"""

import streamlit as st
import openai
import anthropic
import tempfile
import os
import io
import time
import math
import subprocess
from datetime import datetime
from pathlib import Path

# ─── Page Config ───
st.set_page_config(
    page_title="LectureChor",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ─── Custom CSS (Professional Dark Theme with Visual Flair) ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    /* ===== GLOBAL ===== */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: #0B0F1A;
        color: #E2E8F0;
    }

    /* Animated gradient mesh background */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background:
            radial-gradient(ellipse at 20% 50%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 20%, rgba(168, 85, 247, 0.06) 0%, transparent 50%),
            radial-gradient(ellipse at 50% 80%, rgba(59, 130, 246, 0.05) 0%, transparent 50%);
        pointer-events: none;
        z-index: 0;
    }

    /* ===== HERO HEADER ===== */
    .hero {
        text-align: center;
        padding: 2rem 0 1rem;
        position: relative;
    }
    .hero-icon {
        font-size: 3.5rem;
        margin-bottom: 0.5rem;
        display: block;
        filter: drop-shadow(0 0 20px rgba(99, 102, 241, 0.4));
    }
    .hero h1 {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #818CF8 0%, #C084FC 40%, #F472B6 70%, #FB923C 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
        letter-spacing: -1.5px;
    }
    .hero .tagline {
        font-size: 1.1rem;
        color: #94A3B8;
        font-weight: 400;
        font-style: italic;
    }
    .hero .sub-tagline {
        font-size: 0.8rem;
        color: #475569;
        margin-top: 0.3rem;
    }

    /* ===== GLASS CARD ===== */
    .glass-card {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(99, 102, 241, 0.15);
        border-radius: 20px;
        padding: 2rem;
        backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        position: relative;
        overflow: hidden;
    }
    .glass-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.3), transparent);
    }

    /* ===== UPLOAD AREA ===== */
    [data-testid="stFileUploader"] {
        border: 2px dashed rgba(99, 102, 241, 0.3) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        background: rgba(99, 102, 241, 0.03) !important;
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(99, 102, 241, 0.6) !important;
        background: rgba(99, 102, 241, 0.06) !important;
    }

    /* ===== BUTTONS ===== */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #A855F7 100%) !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 0.8rem 2rem !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        letter-spacing: 0.5px;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4) !important;
        text-transform: uppercase;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-3px) scale(1.02) !important;
        box-shadow: 0 8px 30px rgba(99, 102, 241, 0.5) !important;
    }

    /* ===== STATUS CARDS ===== */
    .status-card {
        padding: 1rem 1.4rem;
        border-radius: 14px;
        margin: 0.5rem 0;
        font-size: 0.95rem;
        backdrop-filter: blur(10px);
    }
    .status-processing {
        background: rgba(251, 191, 36, 0.08);
        border-left: 4px solid #F59E0B;
        color: #FCD34D;
    }
    .status-done {
        background: rgba(16, 185, 129, 0.08);
        border-left: 4px solid #10B981;
        color: #6EE7B7;
    }
    .status-error {
        background: rgba(239, 68, 68, 0.08);
        border-left: 4px solid #EF4444;
        color: #FCA5A5;
    }

    /* ===== STATS ROW ===== */
    .stats-row {
        display: flex;
        gap: 1rem;
        margin: 1rem 0;
    }
    .stat-box {
        flex: 1;
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(99, 102, 241, 0.12);
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .stat-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, #6366F1, #A855F7);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    .stat-box:hover {
        transform: translateY(-3px);
        border-color: rgba(99, 102, 241, 0.3);
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.15);
    }
    .stat-box:hover::before {
        opacity: 1;
    }
    .stat-box .num {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.6rem;
        font-weight: 700;
        background: linear-gradient(135deg, #818CF8, #C084FC);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stat-box .label {
        font-size: 0.7rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
        margin-top: 0.4rem;
    }

    /* ===== PASSWORD SCREEN ===== */
    .password-screen {
        max-width: 400px;
        margin: 4rem auto;
        text-align: center;
    }
    .password-screen .lock-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        display: block;
        filter: drop-shadow(0 0 15px rgba(99, 102, 241, 0.3));
    }
    .password-screen h2 {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #818CF8, #C084FC);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    .password-screen .subtitle {
        color: #64748B;
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
    }

    /* ===== DOWNLOAD BUTTONS ===== */
    .stDownloadButton > button {
        width: 100%;
        border-radius: 12px !important;
        padding: 0.7rem !important;
        font-weight: 600 !important;
        background: rgba(99, 102, 241, 0.08) !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        color: #C7D2FE !important;
        transition: all 0.3s ease !important;
    }
    .stDownloadButton > button:hover {
        border-color: rgba(99, 102, 241, 0.5) !important;
        background: rgba(99, 102, 241, 0.15) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.2) !important;
    }

    /* ===== SECTION DIVIDER ===== */
    .section-divider {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin: 1.5rem 0;
    }
    .section-divider .line {
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.2), transparent);
    }
    .section-divider .icon {
        color: #6366F1;
        font-size: 1.2rem;
    }

    /* ===== FEATURE PILLS ===== */
    .feature-pills {
        display: flex;
        justify-content: center;
        gap: 0.8rem;
        margin: 1rem 0;
        flex-wrap: wrap;
    }
    .pill {
        background: rgba(99, 102, 241, 0.08);
        border: 1px solid rgba(99, 102, 241, 0.15);
        border-radius: 100px;
        padding: 0.4rem 1rem;
        font-size: 0.75rem;
        color: #A5B4FC;
        font-weight: 500;
        letter-spacing: 0.3px;
    }

    /* ===== DEFAULTS CLEANUP ===== */
    header[data-testid="stHeader"] {
        background: transparent;
    }
    .block-container {
        max-width: 780px;
        padding-top: 1rem;
    }
    hr {
        border-color: rgba(99, 102, 241, 0.1) !important;
    }
    .stTextInput input {
        border-radius: 12px !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        background: rgba(15, 23, 42, 0.8) !important;
        color: #E2E8F0 !important;
        transition: all 0.3s ease !important;
    }
    .stTextInput input:focus {
        border-color: #6366F1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
    }

    /* ===== FOOTER ===== */
    .app-footer {
        text-align: center;
        padding: 2rem 0 1rem;
        margin-top: 3rem;
        position: relative;
    }
    .app-footer::before {
        content: '';
        position: absolute;
        top: 0;
        left: 20%;
        right: 20%;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.2), transparent);
    }
    .app-footer .footer-brand {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.85rem;
        color: #475569;
        font-weight: 500;
    }
    .app-footer .footer-sub {
        font-size: 0.7rem;
        color: #334155;
        margin-top: 0.3rem;
    }
    .app-footer .easter-egg {
        font-size: 0.65rem;
        color: #1E293B;
        margin-top: 0.5rem;
        cursor: default;
        transition: color 0.5s ease;
    }
    .app-footer .easter-egg:hover {
        color: #6366F1;
    }
</style>
""", unsafe_allow_html=True)

# ─── Constants ───
MAX_CHUNK_SIZE_MB = 24
WHISPER_MODEL = "whisper-1"
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# ─── Password Protection ───
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "lawnotes2026")

def check_password():
    """Password gate with clean design."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True

    st.markdown("""
    <div class="password-screen">
        <span class="lock-icon">🔒</span>
        <h2>LectureChor</h2>
        <p class="subtitle">You skip class. We take notes.</p>
    </div>
    """, unsafe_allow_html=True)

    pwd = st.text_input("Password", type="password", key="pwd_input", label_visibility="collapsed", placeholder="Enter password to continue...")
    if st.button("Unlock", use_container_width=True, type="primary"):
        if pwd == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Wrong password. Are you sure you're a LectureChor?")

    st.markdown("""
    <div style="text-align: center; margin-top: 2rem;">
        <span style="font-size: 0.75rem; color: #334155;">Hint: Ask a fellow chor</span>
    </div>
    """, unsafe_allow_html=True)
    return False

def get_file_size_mb(filepath):
    return os.path.getsize(filepath) / (1024 * 1024)

def split_audio(filepath):
    """Split audio files > 24MB into chunks."""
    size_mb = get_file_size_mb(filepath)
    if size_mb <= MAX_CHUNK_SIZE_MB:
        return [filepath]

    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", filepath],
        capture_output=True, text=True
    )
    total_duration = float(result.stdout.strip())
    chunk_duration = int(total_duration * (MAX_CHUNK_SIZE_MB / size_mb))
    chunk_duration = max(300, chunk_duration)

    chunks = []
    tmp_dir = tempfile.mkdtemp()
    start = 0
    chunk_num = 0

    while start < total_duration:
        chunk_num += 1
        chunk_path = os.path.join(tmp_dir, f"chunk_{chunk_num:03d}.mp3")
        actual_start = max(0, start - 30) if chunk_num > 1 else start

        cmd = [
            "ffmpeg", "-y", "-i", filepath,
            "-ss", str(actual_start),
            "-t", str(chunk_duration + (30 if chunk_num > 1 else 0)),
            "-acodec", "libmp3lame", "-ab", "64k", "-ar", "16000",
            chunk_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        chunks.append(chunk_path)
        start += chunk_duration

    return chunks

def transcribe_audio(filepath, subject, progress_callback=None):
    """Transcribe with Whisper API."""
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    chunks = split_audio(filepath)
    full_transcript = []

    for i, chunk_path in enumerate(chunks):
        if progress_callback:
            progress_callback(f"Transcribing{'chunk ' + str(i+1) + '/' + str(len(chunks)) if len(chunks) > 1 else ''}...")

        with open(chunk_path, "rb") as f:
            prompt_text = "This is a law lecture"
            if subject:
                prompt_text += f" on {subject}"
            prompt_text += ". Legal terms, case names, and some Hindi words may appear."

            response = client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=f,
                language="en",
                prompt=prompt_text,
                response_format="text"
            )
        full_transcript.append(response)

    return " ".join(full_transcript)

def generate_notes(transcript, subject, filename):
    """Generate structured notes with Claude — Professor Kanishka Jeph persona."""
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

    subject_expertise = subject if subject else "Indian Law"

    system_prompt = f"""You are Professor Kanishka Jeph, a distinguished legal scholar with over 50 years of experience in Indian law. You hold a D.Litt. in Jurisprudence from the University of Delhi, have argued landmark cases before the Supreme Court of India, and have been a visiting professor at NLU Delhi, NALSAR, and NLU Jodhpur. You are now retired and dedicate your time to mentoring LLM students.

Your specific expertise is in {subject_expertise}, though you are deeply knowledgeable across all branches of Indian law — Constitutional, Criminal, Civil, Administrative, Corporate, Intellectual Property, Environmental, International, Family, Labour, and Taxation law.

You are known for:
- Making complex legal principles crystal clear with real-world Indian examples
- Connecting cases to broader jurisprudential themes
- Pointing out what examiners look for in LLM-level answers
- Using memorable analogies that students never forget
- Noting when a professor's analysis goes beyond the textbook — and why that matters
- Highlighting connections between different areas of Indian law
- Explaining the evolution of legal principles through landmark Indian judgments

Your personality:
- Warm, encouraging, but academically rigorous
- You address students as "beta" or "students" occasionally
- You sometimes share brief anecdotes from your courtroom experience when relevant
- You are passionate about the Indian legal system and its development
- You emphasize understanding over memorization
- You have a dry wit and occasionally make clever observations

When creating notes, your output must be structured as follows:

1. **LECTURE OVERVIEW** — A 3-5 sentence summary of the lecture's scope and key themes, written in your voice as if briefing a student. Add a brief note on why this topic matters in Indian law.

2. **KEY TOPICS** — Each major topic discussed gets its own section with:
   - Clear heading
   - Detailed explanation of the legal principle/concept with Indian context
   - Any statutory provisions mentioned (with section numbers if stated)
   - Practical application or examples given by the professor
   - Your additional insight or connection to broader Indian jurisprudence

3. **CASE LAW REFERENCED** — A dedicated section listing every case mentioned:
   - Case name (formatted properly, e.g., *Maneka Gandhi v. Union of India*)
   - Court and year (if mentioned)
   - Key ratio decidendi or holding
   - How the professor contextualized it
   - Brief exam tip on how to cite this case effectively

4. **KEY DEFINITIONS & LEGAL TERMS** — Every legal term, Latin phrase, or technical concept explained clearly. Include Hindi legal terms with English translation where relevant.

5. **STATUTORY PROVISIONS** — Any Acts, Sections, Articles, or Rules mentioned with full references and how they were discussed. Include recent amendments if applicable.

6. **PROFESSOR'S ANALYSIS & OPINIONS** — Personal insights, critiques, or analytical points from the lecturer. Add a note if this aligns with or diverges from mainstream legal opinion.

7. **EXAM-RELEVANT POINTS** — Points emphasized as important. Structure these as potential exam question themes with brief answer strategies.

8. **CONNECTIONS & CROSS-REFERENCES** — Links to other areas of Indian law, recent judicial trends, and Law Commission recommendations if relevant.

9. **PROFESSOR JEPH'S NOTE** — At the end, add 2-3 personal observations or tips from your decades of experience that would help students truly understand this topic beyond the textbook.

FORMATTING RULES:
- Use clear markdown headings (# for sections, ## for sub-topics, ### for specifics)
- Bold key terms on first mention
- Italicize case names
- Use bullet points for lists of elements/conditions
- Keep language precise and academic but accessible
- If the transcript is unclear at any point, note it as [Unclear in recording]
- If Hindi words appear, include them with English translation where possible
- Preserve the logical flow of the lecture
- Be thorough — capture everything"""

    subject_line = f"**Subject: {subject}**\n" if subject else ""

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8000,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": f"""{subject_line}
**Source:** {filename}
**Date:** {datetime.now().strftime('%B %d, %Y')}

Below is the full transcript of a law lecture. Create comprehensive, structured notes following your format. Be exhaustive — capture every legal concept, case, definition, and statutory provision mentioned. Add your expert insights where valuable.

---

TRANSCRIPT:
{transcript}

---

Generate complete structured notes now, Professor Jeph."""
        }]
    )

    return message.content[0].text

def create_docx_bytes(notes_text, subject, filename):
    """Create a Word document and return as bytes."""
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import re

    doc = Document()

    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)
    style.paragraph_format.line_spacing = 1.15

    for level, (size, color) in enumerate([
        (Pt(18), RGBColor(0x1B, 0x3A, 0x5C)),
        (Pt(14), RGBColor(0x2E, 0x75, 0xB6)),
        (Pt(12), RGBColor(0x40, 0x40, 0x40)),
    ], 1):
        h = doc.styles[f'Heading {level}']
        h.font.name = 'Calibri'
        h.font.size = size
        h.font.color.rgb = color
        h.font.bold = True

    doc.add_paragraph()
    doc.add_paragraph()
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("LECTURE NOTES")
    r.font.size = Pt(32)
    r.font.color.rgb = RGBColor(0x1B, 0x3A, 0x5C)
    r.font.bold = True

    if subject:
        s = doc.add_paragraph()
        s.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = s.add_run(subject.upper())
        r.font.size = Pt(18)
        r.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    m = doc.add_paragraph()
    m.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = m.add_run(f"Generated: {datetime.now().strftime('%B %d, %Y')}\nSource: {filename}\nBy LectureChor AI")
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

    doc.add_page_break()

    for line in notes_text.split('\n'):
        line = line.rstrip()
        if not line:
            continue
        if line.startswith('### '):
            doc.add_heading(line[4:].strip().replace('**', ''), level=3)
        elif line.startswith('## '):
            doc.add_heading(line[3:].strip().replace('**', ''), level=2)
        elif line.startswith('# '):
            doc.add_heading(line[2:].strip().replace('**', ''), level=1)
        elif line.startswith('- ') or line.startswith('* '):
            text = line[2:].strip()
            p = doc.add_paragraph(style='List Bullet')
            _add_formatted_runs(p, text)
        elif line.startswith('  - ') or line.startswith('  * '):
            text = line[4:].strip()
            p = doc.add_paragraph(style='List Bullet 2')
            _add_formatted_runs(p, text)
        elif line.startswith('---'):
            continue
        else:
            p = doc.add_paragraph()
            _add_formatted_runs(p, line)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()

def _add_formatted_runs(paragraph, text):
    """Add text with bold/italic markdown formatting."""
    import re
    parts = re.split(r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*)', text)
    for part in parts:
        if part.startswith('***') and part.endswith('***'):
            r = paragraph.add_run(part[3:-3])
            r.bold = True
            r.italic = True
        elif part.startswith('**') and part.endswith('**'):
            r = paragraph.add_run(part[2:-2])
            r.bold = True
        elif part.startswith('*') and part.endswith('*'):
            r = paragraph.add_run(part[1:-1])
            r.italic = True
        else:
            paragraph.add_run(part)

# ═══════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════

if not check_password():
    st.stop()

# Hero
st.markdown("""
<div class="hero">
    <span class="hero-icon">🎓</span>
    <h1>LectureChor</h1>
    <p class="tagline">You skip class. We take notes.</p>
    <p class="sub-tagline">Powered by AI that actually paid attention</p>
</div>
""", unsafe_allow_html=True)

# Feature pills
st.markdown("""
<div class="feature-pills">
    <span class="pill">🎙️ Whisper Transcription</span>
    <span class="pill">🧠 Claude AI Notes</span>
    <span class="pill">📄 Word Export</span>
    <span class="pill">🇮🇳 Hindi + English</span>
</div>
""", unsafe_allow_html=True)

# Divider
st.markdown("""
<div class="section-divider">
    <div class="line"></div>
    <span class="icon">✨</span>
    <div class="line"></div>
</div>
""", unsafe_allow_html=True)

# Upload section
col1, col2 = st.columns([2, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Drop your lecture audio here",
        type=["mp3", "m4a", "wav", "mp4", "ogg", "flac", "webm"],
        help="Supports MP3, M4A, WAV, MP4, OGG, FLAC, WebM — up to 500MB"
    )

with col2:
    subject = st.text_input(
        "Subject",
        placeholder="e.g., Constitutional Law",
        help="Helps AI focus on the right area of law"
    )

# Process button
if uploaded_file is not None:
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)

    st.markdown(f"""
    <div class="stats-row">
        <div class="stat-box">
            <div class="num">{uploaded_file.name.split('.')[-1].upper()}</div>
            <div class="label">Format</div>
        </div>
        <div class="stat-box">
            <div class="num">{file_size_mb:.1f} MB</div>
            <div class="label">File size</div>
        </div>
        <div class="stat-box">
            <div class="num">{subject or 'Auto'}</div>
            <div class="label">Subject</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("⚡ Generate Notes", use_container_width=True, type="primary"):

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        try:
            # Step 1: Transcribe
            with st.status("🎙️ Transcribing audio with Whisper AI...", expanded=True) as status:
                st.write(f"Processing {file_size_mb:.1f}MB audio file...")
                start_time = time.time()
                transcript = transcribe_audio(tmp_path, subject)
                word_count = len(transcript.split())
                transcribe_time = time.time() - start_time
                st.write(f"✅ Transcription complete — {word_count:,} words in {transcribe_time:.0f}s")
                status.update(label="✅ Transcription complete", state="complete")

            # Step 2: Generate Notes
            with st.status("🧠 Professor Jeph is preparing your notes...", expanded=True) as status:
                st.write("Analyzing transcript for legal concepts, case law, definitions...")
                start_time = time.time()
                notes = generate_notes(transcript, subject, uploaded_file.name)
                notes_time = time.time() - start_time
                st.write(f"✅ Notes generated in {notes_time:.0f}s")
                status.update(label="✅ Notes generated by Prof. Jeph", state="complete")

            # Step 3: Display Results
            st.markdown("""
            <div class="section-divider">
                <div class="line"></div>
                <span class="icon">📚</span>
                <div class="line"></div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("### 📋 Your Notes Are Ready")

            # Stats
            total_time = transcribe_time + notes_time
            st.markdown(f"""
            <div class="stats-row">
                <div class="stat-box">
                    <div class="num">{word_count:,}</div>
                    <div class="label">Words transcribed</div>
                </div>
                <div class="stat-box">
                    <div class="num">{total_time:.0f}s</div>
                    <div class="label">Total time</div>
                </div>
                <div class="stat-box">
                    <div class="num">₹{int((word_count/1000)*4 + 30):,}</div>
                    <div class="label">Est. cost</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # DOWNLOADS AT THE TOP
            st.markdown("#### 📥 Download")
            col_a, col_b, col_c = st.columns(3)
            safe_name = subject.replace(' ', '_')[:20] if subject else "Lecture"

            with col_a:
                docx_bytes = create_docx_bytes(notes, subject, uploaded_file.name)
                st.download_button(
                    "📄 Word Document",
                    data=docx_bytes,
                    file_name=f"LectureChor_{safe_name}_{datetime.now().strftime('%Y%m%d')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

            with col_b:
                md_content = f"# Lecture Notes: {subject or uploaded_file.name}\n"
                md_content += f"*Generated by LectureChor: {datetime.now().strftime('%B %d, %Y')}*\n\n"
                md_content += notes
                st.download_button(
                    "📝 Markdown",
                    data=md_content,
                    file_name=f"LectureChor_{safe_name}_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )

            with col_c:
                st.download_button(
                    "🎙️ Transcript",
                    data=transcript,
                    file_name=f"Transcript_{safe_name}_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            st.markdown("""
            <div class="section-divider">
                <div class="line"></div>
                <span class="icon">📖</span>
                <div class="line"></div>
            </div>
            """, unsafe_allow_html=True)

            # Notes display (AFTER download buttons)
            st.markdown(notes)

            # Save to session
            st.session_state['last_notes'] = notes
            st.session_state['last_transcript'] = transcript

        except Exception as e:
            st.markdown(f"""
            <div class="status-card status-error">
                ❌ <strong>Error:</strong> {str(e)}
            </div>
            """, unsafe_allow_html=True)
            st.error(f"Full error: {e}")

        finally:
            os.unlink(tmp_path)

# Footer with easter eggs
st.markdown("""
<div class="app-footer">
    <div class="footer-brand">🎓 Built by KJ for LectureChors</div>
    <div class="footer-sub">Whisper AI + Claude | Made with sleep deprivation and chai</div>
    <div class="easter-egg">v2.0 — KJ was here — jeph.exe has stopped working</div>
</div>
""", unsafe_allow_html=True)
