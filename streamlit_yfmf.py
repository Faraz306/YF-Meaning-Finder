import os
import re
from pathlib import Path

import tkinter as tk
from tkinter import filedialog
import streamlit as st
import scrubadub
from google import genai

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="YF Meaning Finder",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CUSTOM UI
# ============================================================

st.markdown(
    """
<style>
/* Main page */
.stApp {
    background: radial-gradient(
        circle at top right,
        rgba(80, 80, 255, 0.10),
        transparent 35%
    ),
    linear-gradient(
        135deg,
        #08090d 0%,
        #0d1018 50%,
        #08090d 100%
    );
}

/* Main content width */
.block-container {
    max-width: 1100px;
    padding-top: 3rem;
    padding-bottom: 4rem;
}

/* Header */
.yf-header {
    padding: 25px 30px;
    border-radius: 24px;
    background: linear-gradient(
        135deg,
        rgba(255,255,255,0.08),
        rgba(255,255,255,0.025)
    );
    border: 1px solid rgba(255,255,255,0.10);
    box-shadow: 0 20px 60px rgba(0,0,0,0.35);
    margin-bottom: 25px;
}

.yf-title {
    font-size: 38px;
    font-weight: 800;
    letter-spacing: -1px;
    margin-bottom: 5px;
}

.yf-subtitle {
    color: #a7adba;
    font-size: 16px;
}

/* Cards */
.yf-card {
    padding: 22px;
    border-radius: 20px;
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 18px;
}

.yf-card-title {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 8px;
}

.yf-card-description {
    color: #9da4b3;
    font-size: 14px;
}

/* Folder display */
.folder-display {
    padding: 14px 16px;
    border-radius: 14px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    font-family: monospace;
    color: #dce1ea;
    margin-top: 8px;
    overflow-x: auto;
}

/* Search button */
div.stButton > button {
    width: 100%;
    min-height: 50px;
    border-radius: 14px;
    font-size: 16px;
    font-weight: 700;
    border: 1px solid rgba(255,255,255,0.12);
    transition: all 0.2s ease;
}

div.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(0,0,0,0.30);
}

/* Input fields */
div[data-baseweb="input"] {
    border-radius: 13px;
}

/* Match cards */
.match-header {
    padding: 14px 18px;
    border-radius: 14px;
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
    margin-top: 15px;
    margin-bottom: 8px;
}

.match-number {
    font-size: 18px;
    font-weight: 750;
}

.match-path {
    color: #9fa6b5;
    font-family: monospace;
    font-size: 13px;
    margin-top: 5px;
    word-break: break-all;
}

/* Small badges */
.badge {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.08);
    color: #cbd1dc;
    font-size: 12px;
    margin-right: 5px;
}

/* Footer */
.yf-footer {
    text-align: center;
    color: #646b78;
    font-size: 12px;
    margin-top: 35px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# FOLDER PICKER
# ============================================================

def choose_folder():
    """
    Opens the operating system's native folder picker.
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder = filedialog.askdirectory(
        title="Select folder to search"
    )
    root.destroy()
    return folder

# ============================================================
# PRIVACY FILTER
# ============================================================

def scrub_sensitive_data(text: str) -> str:
    patterns = {
        "api_keys": (
            r"\b("
            r"gsk_[a-zA-Z0-9]{30,60}"
            r"|AIzaSy[a-zA-Z0-9_\-]{33}"
            r"|[a-zA-Z0-9]{32,48}"
            r")\b"
        ),
        "numbers": (
            r"\b\d{4,}[-.\s]?\d{4,}\b"
            r"|\b\d{10,12}\b"
        ),
    }

    cleaned_text = text

    for pattern in patterns.values():
        cleaned_text = re.sub(
            pattern,
            "{private_data}",
            cleaned_text,
        )

    try:
        scrubber = scrubadub.Scrubber()
        cleaned_text = scrubber.clean(
            cleaned_text
        )
    except Exception:
        pass

    cleaned_text = re.sub(
        r"\{\{[A-Z_]+\}\}",
        "{private_data}",
        cleaned_text,
    )

    return cleaned_text

# ============================================================
# READ FILES
# ============================================================

def read_files(location: str) -> list:

    allowed_extensions = (
        ".py",
        ".txt",
        ".csv",
        ".md",
        ".json",
    )

    scanned_files = []

    for root, dirs, files in os.walk(location):

        # Ignore common huge/unnecessary directories
        dirs[:] = [
            d for d in dirs
            if d not in {
                ".git",
                "__pycache__",
                "node_modules",
                ".venv",
                "venv",
                "env",
            }
        ]

        for file in files:

            if not file.lower().endswith(
                allowed_extensions
            ):
                continue

            full_path = Path(root) / file

            try:

                with open(
                    full_path,
                    "r",
                    encoding="utf-8",
                    errors="ignore",
                ) as f:

                    # Read only the first 4000 characters
                    raw_text = f.read(4000)

                safe_text = scrub_sensitive_data(
                    raw_text
                )

                scanned_files.append(
                    {
                        "path": str(full_path),
                        "content": safe_text,
                    }
                )

            except Exception:
                continue

    return scanned_files

# ============================================================
# GEMINI ANALYSIS
# ============================================================

def analyze_files_with_gemini(
    files_data: list,
    user_query: str,
    api_key: str,
) -> str:

    if not files_data:
        return "No text-based files found."

    # IMPORTANT:
    # The API key comes ONLY from the Streamlit input.
    client = genai.Client(
        api_key=api_key
    )

    payload = []

    for i, file_info in enumerate(files_data):

        payload.append(
            f"--- FILE {i} ---"
        )

        payload.append(
            f"Path: {file_info['path']}"
        )

        payload.append(
            f"Content:\n{file_info['content']}"
        )

        payload.append(
            "-" * 30
        )

    all_files_text = "\n".join(payload)

    prompt = f"""
You are YF Core Engine.

The user is trying to find a local file based on what they remember about its contents.

USER DESCRIPTION:
"{user_query}"

Below are files from the user's directory.

Sensitive information has already been replaced with {{private_data}}.

=== FILE DATA ===

{all_files_text}

=== END FILE DATA ===

Find the files that best match the user's request.

Return ONLY the exact file paths.

Rules:
- One path per line.
- Do not explain anything.
- Do not use markdown.
- Do not invent paths.
- Only return paths that appear in the FILE DATA.
"""

    try:

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )

        return response.text.strip()

    except Exception as e:

        return f"API Error: {e}"

# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
<div class="yf-header">
    <div class="yf-title">
        🔎 YF Meaning Finder
    </div>
    <div class="yf-subtitle">
        Find forgotten files by describing what you remember.
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================================
# MAIN INPUT CARD
# ============================================================

st.markdown(
    """
<div class="yf-card">
    <div class="yf-card-title">
        📂 Choose your workspace
    </div>
    <div class="yf-card-description">
        Select the folder containing your projects. YF Meaning Finder will scan supported text files inside it.
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================================
# FOLDER PICKER
# ============================================================

folder_col1, folder_col2 = st.columns(
    [4, 1],
    vertical_alignment="center",
)

with folder_col1:
    folder_path = st.session_state.get(
        "folder_path",
        "",
    )
    if folder_path:
        st.markdown(
            f"""
<div class="folder-display">
    📁 {folder_path}
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        st.info(
            "No folder selected yet."
        )

with folder_col2:
    if st.button(
        "📂 Browse",
        use_container_width=True,
    ):
        selected_folder = choose_folder()
        if selected_folder:
            st.session_state[
                "folder_path"
            ] = selected_folder
            st.rerun()

# ============================================================
# QUERY CARD
# ============================================================

st.markdown(
    """
<div class="yf-card">
    <div class="yf-card-title">
        🧠 What do you remember?
    </div>
    <div class="yf-card-description">
        Describe the file naturally. You don't need to remember its filename.
    </div>
</div>
""",
    unsafe_allow_html=True,
)

user_query = st.text_input(
    "File description",
    placeholder=(
        "Example: the Python file where I made "
        "the fraud detector"
    ),
    label_visibility="collapsed",
)

# ============================================================
# API KEY CARD
# ============================================================

st.markdown(
    """
<div class="yf-card">
    <div class="yf-card-title">
        🔐 Gemini API Key
    </div>
    <div class="yf-card-description">
        Your key is entered locally into this session and is not hard-coded into the application.
    </div>
</div>
""",
    unsafe_allow_html=True,
)

api_key = st.text_input(
    "Gemini API Key",
    type="password",
    placeholder="Paste your Gemini API key here",
    label_visibility="collapsed",
)

# ============================================================
# SEARCH BUTTON
# ============================================================

st.write("")

search_clicked = st.button(
    "🔎 Find Matching Files",
    type="primary",
    use_container_width=True,
)

# ============================================================
# SEARCH
# ============================================================

if search_clicked:

    folder_path = st.session_state.get(
        "folder_path",
        "",
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not folder_path:
        st.error(
            "📂 Please choose a folder first."
        )
        st.stop()

    if not os.path.isdir(folder_path):
        st.error(
            "❌ The selected folder no longer exists."
        )
        st.stop()

    if not user_query.strip():
        st.error(
            "🧠 Please describe the file you are looking for."
        )
        st.stop()

    if not api_key.strip():
        st.error(
            "🔐 Please enter your Gemini API key."
        )
        st.stop()

    # ========================================================
    # SCAN
    # ========================================================

    with st.spinner(
        "📂 Scanning your workspace..."
    ):

        files_data = read_files(
            folder_path
        )

    # ========================================================
    # SCAN RESULT
    # ========================================================

    if not files_data:
        st.warning(
            "No supported text files were found."
        )
        st.stop()

    st.markdown(
        f"""
<div style="
    padding: 12px 16px;
    border-radius: 14px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    margin: 15px 0;
">
    📄 <b>{len(files_data)}</b> supported files scanned
</div>
""",
        unsafe_allow_html=True,
    )

    # ========================================================
    # GEMINI
    # ========================================================

    with st.spinner(
        "🤖 YF Core Engine is finding matches..."
    ):

        result = analyze_files_with_gemini(
            files_data,
            user_query,
            api_key,
        )

    # ========================================================
    # MATCHED FILES
    # ========================================================

    st.divider()

    st.subheader(
        "🎯 Matching Files"
    )

    paths = []

    for line in result.splitlines():

        path = line.strip().strip("`").strip()

        if not path:
            continue

        # Only accept actual files
        if os.path.isfile(path):

            # Avoid duplicate results
            if path not in paths:
                paths.append(path)

    # ========================================================
    # DISPLAY RESULTS
    # ========================================================

    if paths:

        st.success(
            f"Found {len(paths)} matching file(s)."
        )

        for index, path in enumerate(
            paths[:5],
            start=1,
        ):

            st.markdown(
                f"""
<div class="match-header">
    <div class="match-number">
        📄 Match {index}
    </div>
    <div class="match-path">
        {path}
    </div>
</div>
""",
                unsafe_allow_html=True,
            )

            try:

                with open(
                    path,
                    "r",
                    encoding="utf-8",
                    errors="ignore",
                ) as f:

                    file_content = f.read()

                # ----------------------------------------
                # File metadata
                # ----------------------------------------

                file_size = os.path.getsize(
                    path
                )

                extension = (
                    Path(path)
                    .suffix
                    .replace(".", "")
                    .upper()
                )

                col1, col2 = st.columns(2)

                with col1:
                    st.caption(
                        f"📦 {file_size:,} bytes"
                    )

                with col2:
                    st.caption(
                        f"📝 {extension or 'TEXT'}"
                    )

                # ----------------------------------------
                # File contents
                # ----------------------------------------

                with st.expander(
                    "👁️ View file contents",
                    expanded=True,
                ):

                    st.code(
                        file_content,
                        language=(
                            Path(path)
                            .suffix
                            .replace(".", "")
                        ),
                    )

            except Exception as e:

                st.error(
                    f"Could not read file: {e}"
                )

    else:

        st.warning(
            "No matching files were found."
        )

        with st.expander(
            "Show Gemini response"
        ):

            st.code(
                result
            )

# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
<div class="yf-footer">
    YF Meaning Finder • Local file discovery powered by AI
</div>
""",
    unsafe_allow_html=True,
)
