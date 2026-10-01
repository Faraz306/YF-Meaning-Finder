import os
import re
from pathlib import Path

import streamlit as st
import scrubadub
from google import genai


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

    scrubber = scrubadub.Scrubber()

    cleaned_text = scrubber.clean(
        cleaned_text
    )

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

    client = genai.Client(
        api_key="AQ.Ab8RN6JkfKjLfzRLS91mYYvyc-JdSTCnjF-b0yco25VAWIXeTQ "
    )

    payload = []

    for i, file_info in enumerate(
        files_data
    ):

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

Below are files from the user's directory.

Sensitive information has been replaced with
{{private_data}}.

=== FILE DATA ===

{all_files_text}

=== END FILE DATA ===

Find the files that best match the user's request.

Return ONLY the exact file paths,
one path per line.

Do not explain anything.
Do not use markdown.
Do not invent paths.
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
# STREAMLIT APP
# ============================================================

st.title("🔎 YF Meaning Finder")

st.write(
    "Find files by describing what you remember "
    "about their contents."
)


# ============================================================
# FOLDER
# ============================================================

folder_path = st.text_input(
    "Folder path",
    placeholder=r"C:\Users\Faraz\PycharmProjects",
)


# ============================================================
# SEARCH
# ============================================================

user_query = st.text_input(
    "What do you remember about the file?",
    placeholder=(
        "Example: the Python file where I made "
        "the fraud detector"
    ),
)


# ============================================================
# API KEY
# ============================================================

api_key = st.text_input(
    "Gemini API Key",
    type="password",
)


# ============================================================
# SEARCH
# ============================================================

if st.button("🔎 Find Files"):

    if not folder_path:
        st.error("Please enter a folder path.")
        st.stop()

    if not os.path.isdir(folder_path):
        st.error("Folder does not exist.")
        st.stop()

    if not user_query.strip():
        st.error("Please describe the file.")
        st.stop()

    if not api_key.strip():
        st.error("Please enter your Gemini API key.")
        st.stop()


    # ========================================================
    # SCAN FILES
    # ========================================================

    with st.spinner("📂 Reading files..."):

        files_data = read_files(
            folder_path
        )

    st.write(
        f"📄 Scanned {len(files_data)} files."
    )


    # ========================================================
    # GEMINI
    # ========================================================

    with st.spinner(
        "🤖 Finding matching files..."
    ):

        result = analyze_files_with_gemini(
            files_data,
            user_query,
            api_key,
        )


    # ========================================================
    # MATCHED FILES
    # ========================================================

    st.subheader(
        "🎯 Matching Files"
    )

    paths = []

    for line in result.splitlines():

        path = line.strip().strip("`")

        if path and os.path.isfile(path):

            paths.append(path)


    # ========================================================
    # DISPLAY CONTENT
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
                f"### 📄 Match {index}"
            )

            st.write(
                f"**Path:** `{path}`"
            )

            try:

                with open(
                    path,
                    "r",
                    encoding="utf-8",
                    errors="ignore",
                ) as f:

                    file_content = f.read()

                # ------------------------------------------------
                # Show content in expandable section
                # ------------------------------------------------

                with st.expander(
                    "View file contents",
                    expanded=True,
                ):

                    st.code(
                        file_content,
                        language=(
                            Path(path).suffix
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

        st.write(
            "Gemini response:"
        )

        st.code(
            result
        )
