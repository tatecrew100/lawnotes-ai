"""
LawNotes AI — Web App
Lecture Audio → Professional Law Notes
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
    page_title="LawNotes AI",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ─── Custom CSS ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Serif+Display&display=swap');

    /* Global */
    .stApp {
        font-family: 'DM Sans', sans-serif;
    }

    /* Hero header */
    .hero {
        text-align: center;
        padding: 2rem 0 1rem;
    }
    .hero h1 {
        font-family: 'DM Serif Display', serif;
        font-size: 2.8rem;
        color: #1B3A5C;
        margin-bottom: 0.3rem;
        letter-spacing: -0.5px;
    }
    .hero p {
        font-size: 1.1rem;
        color: #6B7280;
        margin-top: 0;
    }

    /* Status cards */
    .status-card {
        padding: 1rem 1.2rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        font-size: 0.95rem;
    }
    .status-processing {
        background: #FEF3C7;
        border-left: 4px solid #F59E0B;
        color: #92400E;
    }
    .status-done {
        background: #D1FAE5;
        border-left: 4px solid #10B981;
        color: #065F46;
    }
    .status-error {
        background: #FEE2E2;
        border-left: 4px solid #EF4444;
        color: #991B1B;
    }

    /* Notes output */
    .notes-container {
        background: #FAFAFA;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 2rem;
        margin: 1rem 0;
        font-size: 0.95rem;
        line-height: 1.7;
    }

    /* Stats row */
    .stats-row {
        display: flex;
        gap: 1rem;
        margin: 1rem 0;
    }
    .stat-box {
        flex: 1;
        background: #F3F4F6;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        text-align: center;
    }
    .stat-box .num {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1B3A5C;
    }
    .stat-box .label {
        font-size: 0.8rem;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Password screen */
    .password-box {
        max-width: 400px;
        margin: 4rem auto;
        text-align: center;
    }

    /* Clean up Streamlit defaults */
    .stDownloadButton > button {
        width: 100%;
        border-radius: 10px;
        padding: 0.6rem;
        font-weight: 600;
    }
    header[data-testid="stHeader"] {
        background: transparent;
    }
    .block-container {
        max-width: 750px;
        padding-top: 1rem;
    }

    /* Dark mode adjustments */
    @media (prefers-color-scheme: dark) {
        .hero h1 { color: #93C5FD; }
        .notes-container { background: #1F2937; border-color: #374151; }
        .stat-box { background: #1F2937; }
        .stat-box .num { color: #93C5FD; }
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
    """Simple password gate."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.markdown('<div class="password-box">', unsafe_allow_html=True)
    st.markdown("## ⚖️ LawNotes AI")
    st.markdown("Enter the password to access")
    pwd = st.text_input("Password", type="password", key="pwd_input")
    if st.button("Enter", use_container_width=True):
        if pwd == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")
    st.markdown('</div>', unsafe_allow_html=True)
    return False


def get_file_size_mb(filepath):
    return os.path.getsize(filepath) / (1024 * 1024)


def split_audio(filepath):
    """Split audio files > 24MB into chunks."""
    size_mb = get_file_size_mb(filepath)
    if size_mb <= MAX_CHUNK_SIZE_MB:
        return [filepath]

    # Get duration using ffprobe
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
    """Generate structured notes with Claude."""
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

    system_prompt = """You are an elite legal academic assistant specializing in creating 
comprehensive law notes from lecture transcripts. Your notes are used by LLM (Masters of Law) 
students who need rigorous, exam-ready material.

Your output must be structured as follows:

1. **LECTURE OVERVIEW** — A 3-5 sentence summary of the lecture's scope and key themes.

2. **KEY TOPICS** — Each major topic discussed gets its own section with:
   - Clear heading
   - Detailed explanation of the legal principle/concept
   - Any statutory provisions mentioned (with section numbers if stated)
   - Practical application or examples given by the professor

3. **CASE LAW REFERENCED** — A dedicated section listing every case mentioned:
   - Case name (formatted properly, e.g., *Maneka Gandhi v. Union of India*)
   - Court and year (if mentioned)
   - Key ratio decidendi or holding
   - How the professor contextualized it

4. **KEY DEFINITIONS & LEGAL TERMS** — Every legal term, Latin phrase, or technical 
   concept explained clearly with context.

5. **STATUTORY PROVISIONS** — Any Acts, Sections, Articles, or Rules mentioned with 
   full references and how they were discussed.

6. **PROFESSOR'S ANALYSIS & OPINIONS** — Personal insights, critiques, or analytical 
   points that go beyond textbook content.

7. **EXAM-RELEVANT POINTS** — Points the professor emphasized as important or likely exam material.

8. **CONNECTIONS & CROSS-REFERENCES** — Links to other areas of law referenced.

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

Below is the full transcript of a law lecture. Create comprehensive, structured notes.
Be exhaustive — capture every legal concept, case, definition, and statutory provision mentioned.

---
TRANSCRIPT:
{transcript}
---

Generate complete structured notes now."""
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

    # Styles
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

    # Title page
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
    r = m.add_run(f"Generated: {datetime.now().strftime('%B %d, %Y')}\nSource: {filename}\nBy LawNotes AI")
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

    doc.add_page_break()

    # Content
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
#  MAIN APP
# ═══════════════════════════════════════════

if not check_password():
    st.stop()

# Hero
st.markdown("""
<div class="hero">
    <h1>⚖️ LawNotes AI</h1>
    <p>Upload a lecture recording → Get professional law notes in minutes</p>
</div>
""", unsafe_allow_html=True)

# Divider
st.markdown("---")

# Upload section
col1, col2 = st.columns([2, 1])
with col1:
    uploaded_file = st.file_uploader(
        "Upload lecture audio",
        type=["mp3", "m4a", "wav", "mp4", "ogg", "flac", "webm"],
        help="Supports MP3, M4A, WAV, MP4, OGG, FLAC, WebM — up to 500MB"
    )
with col2:
    subject = st.text_input(
        "Subject",
        placeholder="e.g., Constitutional Law",
        help="Helps improve transcription accuracy"
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

    if st.button("🚀 Generate Notes", use_container_width=True, type="primary"):

        # Save uploaded file to temp
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        try:
            # ─── Step 1: Transcribe ───
            with st.status("🎙️ Transcribing audio with Whisper AI...", expanded=True) as status:
                st.write(f"Processing {file_size_mb:.1f}MB audio file...")
                start_time = time.time()

                transcript = transcribe_audio(tmp_path, subject)
                word_count = len(transcript.split())
                transcribe_time = time.time() - start_time

                st.write(f"✅ Transcription complete — {word_count:,} words in {transcribe_time:.0f}s")
                status.update(label="✅ Transcription complete", state="complete")

            # ─── Step 2: Generate Notes ───
            with st.status("🧠 Claude is generating structured notes...", expanded=True) as status:
                st.write("Analyzing transcript for legal concepts, case law, definitions...")
                start_time = time.time()

                notes = generate_notes(transcript, subject, uploaded_file.name)
                notes_time = time.time() - start_time

                st.write(f"✅ Notes generated in {notes_time:.0f}s")
                status.update(label="✅ Notes generated", state="complete")

            # ─── Step 3: Display Results ───
            st.markdown("---")
            st.markdown("### 📋 Your Notes")

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

            # Notes display
            st.markdown(notes)

            # ─── Downloads ───
            st.markdown("---")
            st.markdown("### 📥 Download")

            col_a, col_b, col_c = st.columns(3)

            with col_a:
                # Word doc
                docx_bytes = create_docx_bytes(notes, subject, uploaded_file.name)
                safe_name = subject.replace(' ', '_')[:20] if subject else "Lecture"
                st.download_button(
                    "📄 Word Document",
                    data=docx_bytes,
                    file_name=f"Notes_{safe_name}_{datetime.now().strftime('%Y%m%d')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

            with col_b:
                # Markdown
                md_content = f"# Lecture Notes: {subject or uploaded_file.name}\n"
                md_content += f"*Generated: {datetime.now().strftime('%B %d, %Y')}*\n\n"
                md_content += notes
                st.download_button(
                    "📝 Markdown",
                    data=md_content,
                    file_name=f"Notes_{safe_name}_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )

            with col_c:
                # Raw transcript
                st.download_button(
                    "🎙️ Transcript",
                    data=transcript,
                    file_name=f"Transcript_{safe_name}_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            # Save to session for re-download
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
            # Cleanup temp file
            os.unlink(tmp_path)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #9CA3AF; font-size: 0.8rem; padding: 1rem 0;">
    Built with Whisper AI + Claude | LawNotes AI
</div>
""", unsafe_allow_html=True)
