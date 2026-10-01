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
# PRIVACY FILTER
# ============================================================

def scrub_sensitive_data(text: str):

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

        extension = (
            Path(filename)
            .suffix
            .lower()
        )

        if extension not in allowed_extensions:
            continue

        try:

            raw_bytes = uploaded_file.getvalue()

            raw_text = raw_bytes.decode(
                "utf-8",
                errors="ignore",
            )

            # Only send the first 4000 chars
            # of each file to the AI.

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
# GEMINI
# ============================================================

def analyze_files_with_gemini(
    files_data,
    user_query,
    api_key,
):

    if not files_data:

        return "No text-based files found."

    # Uses ONLY the key entered by the user.

    client = genai.Client(
        api_key=api_key
    )

    payload = []

    for index, file_info in enumerate(
        files_data
    ):

        payload.append(
            f"--- FILE {index} ---"
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

    all_files_text = "\n".join(
        payload
    )

    prompt = f"""
You are YF Core Engine.

The user wants to find a file based on memory.

USER DESCRIPTION:
"{user_query}"

The following files were selected by the user.

Sensitive information has already been replaced
with {{private_data}}.

=== FILE DATA ===

{all_files_text}

=== END FILE DATA ===

Find the files that best match the user's description.

Return ONLY the exact file paths from FILE DATA.

Rules:
- One path per line.
- No explanations.
- No markdown.
- Do not invent paths.
- Do not return a path that does not appear in FILE DATA.
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

st.title("🔎 YF Meaning Finder")

st.write(
    "Find forgotten files by describing what you remember."
)


# ============================================================
# FILE UPLOAD
# ============================================================

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
)


# ============================================================
# FILE STATISTICS
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
        if Path(file.name)
        .suffix
        .lower()
        in supported_extensions
    )

    total_count = len(
        uploaded_files
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Files selected",
            total_count,
        )

    with col2:

        st.metric(
            "Supported files",
            supported_count,
        )

    with col3:

        st.metric(
            "Privacy filtering",
            "🔐",
        )


# ============================================================
# QUERY
# ============================================================

st.subheader(
    "🧠 What do you remember about the file?"
)

st.write(
    "Describe the file naturally. "
    "You don't need to remember its filename."
)

user_query = st.text_input(
    "File description",
    placeholder=(
        "Example: the Python file where I made "
        "the fraud detector"
    ),
)


# ============================================================
# API KEY
# ============================================================

st.subheader(
    "🔐 Gemini API Key"
)

st.write(
    "Your API key is used for this search session."
)

api_key = st.text_input(
    "Gemini API Key",
    type="password",
    placeholder="Paste your Gemini API key",
)


# ============================================================
# SEARCH BUTTON
# ============================================================

st.write("")

find_button = st.button(
    "🔎 Find Matching Files",
    type="primary",
    use_container_width=True,
)


# ============================================================
# SEARCH
# ============================================================

if find_button:

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # READ FILES
    # --------------------------------------------------------

    with st.spinner(
        "📂 Reading and protecting your files..."
    ):

        files_data = read_uploaded_files(
            uploaded_files
        )

    if not files_data:

        st.warning(
            "No supported text files were found."
        )

        st.stop()

    # --------------------------------------------------------
    # SCANNED FILE COUNT
    # --------------------------------------------------------

    st.info(
        f"📄 {len(files_data)} supported files "
        f"ready for AI search."
    )

    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    with st.spinner(
        "🤖 YF Core Engine is finding matches..."
    ):

        result = analyze_files_with_gemini(
            files_data,
            user_query,
            api_key,
        )

    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "🎯 Matching Files"
    )

    # --------------------------------------------------------
    # MAP PATHS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # MATCHES
    # --------------------------------------------------------

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

            st.subheader(
                f"📄 Match {index}"
            )

            st.write(
                f"**Path:** `{path}`"
            )

            # ----------------------------------------------
            # FILE CONTENT
            # ----------------------------------------------

            try:

                file_bytes = (
                    uploaded_file.getvalue()
                )

                file_content = (
                    file_bytes.decode(
                        "utf-8",
                        errors="ignore",
                    )
                )

                file_size = len(
                    file_bytes
                )

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

    # --------------------------------------------------------
    # NO MATCH
    # --------------------------------------------------------

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

st.write(
    "YF Meaning Finder • AI-powered local file discovery"
)
