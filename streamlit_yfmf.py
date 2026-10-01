import re
from pathlib import Path

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
)


# ============================================================
# BEAUTIFUL UI
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background:
            radial-gradient(
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

    .block-container {
        max-width: 1100px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
    }

    .yf-header {
        padding: 28px 30px;
        border-radius: 24px;
        background:
            linear-gradient(
                135deg,
                rgba(255,255,255,0.08),
                rgba(255,255,255,0.025)
            );
        border: 1px solid rgba(255,255,255,0.10);
        box-shadow:
            0 20px 60px rgba(0,0,0,0.35);
        margin-bottom: 25px;
    }

    .yf-title {
        font-size: 40px;
        font-weight: 800;
        letter-spacing: -1px;
    }

    .yf-subtitle {
        color: #a7adba;
        font-size: 16px;
        margin-top: 5px;
    }

    .yf-card {
        padding: 22px;
        border-radius: 20px;
        background: rgba(255,255,255,0.045);
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 18px;
    }

    .yf-card-title {
        font-size: 19px;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .yf-card-description {
        color: #9da4b3;
        font-size: 14px;
    }

    .stats-card {
        padding: 18px;
        border-radius: 18px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        text-align: center;
    }

    .stats-number {
        font-size: 27px;
        font-weight: 800;
    }

    .stats-label {
        color: #9299a7;
        font-size: 13px;
    }

    .match-card {
        padding: 18px;
        border-radius: 18px;
        background: rgba(255,255,255,0.045);
        border: 1px solid rgba(255,255,255,0.08);
        margin: 15px 0;
    }

    .match-title {
        font-size: 18px;
        font-weight: 750;
    }

    .match-path {
        color: #9da4b3;
        font-family: monospace;
        font-size: 13px;
        margin-top: 5px;
        word-break: break-all;
    }

    .yf-footer {
        text-align: center;
        color: #626977;
        font-size: 12px;
        margin-top: 35px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


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
# READ UPLOADED FILES
# ============================================================

def read_uploaded_files(uploaded_files):

    allowed_extensions = {
        ".py",
        ".txt",
        ".csv",
        ".md",
        ".json",
    }

    scanned_files = []

    for uploaded_file in uploaded_files:

        filename = uploaded_file.name

        extension = Path(filename).suffix.lower()

        if extension not in allowed_extensions:
            continue

        try:

            raw_bytes = uploaded_file.getvalue()

            raw_text = raw_bytes.decode(
                "utf-8",
                errors="ignore",
            )

            safe_text = scrub_sensitive_data(
                raw_text[:4000]
            )

            scanned_files.append(
                {
                    "path": filename,
                    "content": safe_text,
                    "uploaded_file": uploaded_file,
                }
            )

        except Exception:
            continue

    return scanned_files


# ============================================================
# GEMINI ANALYSIS
# ============================================================

def analyze_files_with_gemini(
    files_data,
    user_query,
    api_key,
):

    if not files_data:
        return "No text-based files found."

    # ========================================================
    # USE THE API KEY ENTERED BY THE USER
    # ========================================================

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

The user is looking for a local file matching:

"{user_query}"

Below are files selected by the user.

Sensitive information has been replaced with
{{private_data}}.

=== FILE DATA ===

{all_files_text}

=== END FILE DATA ===

Find the files that best match the user's request.

Return ONLY the exact file paths from the supplied FILE DATA.

Rules:
- One path per line.
- Do not explain anything.
- Do not use markdown.
- Do not invent paths.
- Do not return files that were not supplied.
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
# FOLDER / DIRECTORY PICKER
# ============================================================

st.markdown(
    """
    <div class="yf-card">

        <div class="yf-card-title">
            📂 Choose your project folder
        </div>

        <div class="yf-card-description">
            Select a folder from your computer.
            YF will receive the files inside the selected
            directory and search through supported text files.
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


uploaded_files = st.file_uploader(
    "Choose a folder",
    type=[
        "py",
        "txt",
        "csv",
        "md",
        "json",
    ],
    accept_multiple_files="directory",
    label_visibility="collapsed",
)


# ============================================================
# FILE COUNT
# ============================================================

if uploaded_files:

    supported_extensions = {
        ".py",
        ".txt",
        ".csv",
        ".md",
        ".json",
    }

    supported_count = sum(
        1
        for file in uploaded_files
        if Path(file.name).suffix.lower()
        in supported_extensions
    )

    total_count = len(uploaded_files)

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            f"""
            <div class="stats-card">
                <div class="stats-number">
                    {total_count}
                </div>
                <div class="stats-label">
                    Files selected
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:

        st.markdown(
            f"""
            <div class="stats-card">
                <div class="stats-number">
                    {supported_count}
                </div>
                <div class="stats-label">
                    Supported files
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:

        st.markdown(
            """
            <div class="stats-card">
                <div class="stats-number">
                    🔐
                </div>
                <div class="stats-label">
                    Privacy filtering
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# QUERY
# ============================================================

st.markdown(
    """
    <div class="yf-card">

        <div class="yf-card-title">
            🧠 What do you remember about the file?
        </div>

        <div class="yf-card-description">
            Describe the file naturally. You don't need
            to remember its filename.
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
# API KEY
# ============================================================

st.markdown(
    """
    <div class="yf-card">

        <div class="yf-card-title">
            🔐 Gemini API Key
        </div>

        <div class="yf-card-description">
            Enter your Gemini API key for this search session.
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


api_key = st.text_input(
    "Gemini API Key",
    type="password",
    placeholder="Paste your Gemini API key",
    label_visibility="collapsed",
)


# ============================================================
# SEARCH BUTTON
# ============================================================

st.write("")

find_button = st.button(
    "🔎  Find Matching Files",
    type="primary",
    use_container_width=True,
)


# ============================================================
# MAIN SEARCH
# ============================================================

if find_button:

    # ========================================================
    # VALIDATION
    # ========================================================

    if not uploaded_files:

        st.error(
            "📂 Please choose a folder first."
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
    # READ FILES
    # ========================================================

    with st.spinner(
        "📂 Reading and protecting your files..."
    ):

        files_data = read_uploaded_files(
            uploaded_files
        )


    if not files_data:

        st.warning(
            "No supported text files were found in the selected folder."
        )

        st.stop()


    # ========================================================
    # SCAN RESULT
    # ========================================================

    st.markdown(
        f"""
        <div class="stats-card">

            <div class="stats-number">
                {len(files_data)}
            </div>

            <div class="stats-label">
                Supported files ready for AI search
            </div>

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
    # RESULTS
    # ========================================================

    st.divider()

    st.subheader(
        "🎯 Matching Files"
    )


    # ========================================================
    # MAP GEMINI PATHS BACK TO UPLOADED FILES
    # ========================================================

    uploaded_map = {
        file_info["path"]: file_info
        for file_info in files_data
    }

    paths = []

    for line in result.splitlines():

        path = (
            line
            .strip()
            .strip("`")
            .strip()
        )

        if not path:
            continue

        if path in uploaded_map:

            if path not in paths:

                paths.append(path)


    # ========================================================
    # DISPLAY MATCHES
    # ========================================================

    if paths:

        st.success(
            f"Found {len(paths)} matching file(s)."
        )


        for index, path in enumerate(
            paths[:5],
            start=1,
        ):

            file_info = uploaded_map[path]

            uploaded_file = (
                file_info["uploaded_file"]
            )


            # ------------------------------------------------
            # MATCH CARD
            # ------------------------------------------------

            st.markdown(
                f"""
                <div class="match-card">

                    <div class="match-title">
                        📄 Match {index}
                    </div>

                    <div class="match-path">
                        {path}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )


            # ------------------------------------------------
            # FILE INFO
            # ------------------------------------------------

            file_bytes = uploaded_file.getvalue()

            file_size = len(file_bytes)

            extension = (
                Path(path)
                .suffix
                .replace(".", "")
                .upper()
            )


            info1, info2 = st.columns(2)

            with info1:

                st.caption(
                    f"📦 {file_size:,} bytes"
                )

            with info2:

                st.caption(
                    f"📝 {extension or 'TEXT'}"
                )


            # ------------------------------------------------
            # ORIGINAL FILE CONTENT
            # ------------------------------------------------

            try:

                original_content = (
                    file_bytes.decode(
                        "utf-8",
                        errors="ignore",
                    )
                )

                with st.expander(
                    "👁️ View file contents",
                    expanded=True,
                ):

                    st.code(
                        original_content,
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


    # ========================================================
    # NO MATCHES
    # ========================================================

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
        YF Meaning Finder • AI-powered local file discovery
    </div>
    """,
    unsafe_allow_html=True,
)