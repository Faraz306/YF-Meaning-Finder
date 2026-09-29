import os
import re
import subprocess
from pathlib import Path
from google import genai
import pandas as pd
import flet as ft
import scrubadub

# ==========================================
# CORE ENGINE MODULES (PRIVACY & ANALYSIS)
# ==========================================

def scrub_sensitive_data(text: str) -> str:
    """
    Yamaan's Custom Privacy Filter.
    Scrubs out active developer API keys, long number configurations,
    emails, and names to prevent external data leakage before sending to Gemini.
    """
    patterns = {
        "api_keys": r"\b(gsk_[a-zA-Z0-9]{30,60}|AIzaSy[a-zA-Z0-9_\-]{33}|[a-zA-Z0-9]{32,48})\b",
        "numbers": r"\b\d{4,}[-.\s]?\d{4,}\b|\b\d{10,12}\b"
    }
    
    cleaned_text = text
    for pattern in patterns.values():
        cleaned_text = re.sub(pattern, "{private_data}", cleaned_text)
        
    scrubber = scrubadub.Scrubber()
    scrubbed_tokens = scrubber.clean(cleaned_text)
    
    final_output = re.sub(r"\{\{[A-Z_]+\}\}", "{private_data}", scrubbed_tokens)
    return final_output


def read_files(location: str) -> list:
    """
    Step 2 Engine: Scans the target directory fast for text formats only (ABCD text).
    Automatically scrubs the raw text data dynamically using your privacy shield.
    """
    allowed_extensions = ('.py', '.txt', '.csv', '.md', '.json')
    scanned_files_package = []
    
    for root, dirs, files in os.walk(location):
        for file in files:
            if file.endswith(allowed_extensions):
                full_path = Path(root) / file
                try:
                    # Read the first 4000 characters per file safely to protect engine RAM speed
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        raw_text = f.read(4000)
                    
                    # Apply privacy protection filter!
                    safe_text = scrub_sensitive_data(raw_text)
                    
                    scanned_files_package.append({
                        "path": str(full_path),
                        "content": safe_text
                    })
                except Exception:
                    continue  # Silently skip locked or corrupted files
                    
    return scanned_files_package


def analyze_files_with_gemini(files_data: list, user_query: str) -> str:
    """
    Step 3 & 4 Engine: Batches the scrubbed data array together safely 
    and sends it to Gemini 3.8 Flash to find paths using semantic meaning.
    """
    if not files_data:
        return "No text-based files found in this directory."
        
    # Pass your key right inside the initialization argument
    client = genai.Client(api_key="AQ.Ab8RN6Juze0UWcxvkkGfqB_lDSp-Pd6Bi6QrCcj9eFU46G3U1A")

    
    payload_builder = []
    for i, file_info in enumerate(files_data):
        payload_builder.append(f"--- FILE ID: {i} ---")
        payload_builder.append(f"Path: {file_info['path']}")
        payload_builder.append(f"Content:\n{file_info['content']}")
        payload_builder.append("-" * 30)
        
    all_files_text = "\n".join(payload_builder)
    
    prompt = f"""
    You are an advanced local file discovery agent called YF Core Engine.
    The user is looking for local files matching this request: "{user_query}"
    
    Below is a compiled dump of text files found in the user's directory. 
    Note: Sensitive personal details have been safely masked as '{{private_data}}' for maximum security.
    
    === FILE DATA START ===
    {all_files_text}
    === FILE DATA END ===
    
    Analyze the contexts and meanings of each file. Identify the paths of the files that precisely answer or match the user's intent.
    Return your answer strictly as a clean list of file paths, one per line. Do not write conversational greetings, markdown ticks, or introduction text.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"API Authentication Error: {str(e)}"

# ==========================================
# MAIN APPLICATION INTERFACE (FLET APPLICATION)
# ==========================================

def main(page: ft.Page):
    page.title = "YF Meaning Finder"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.bgcolor = ft.Colors.TRANSPARENT
    page.padding = 0
    page.spacing = 0

    selected_folder_path = None

    status_text = ft.Text(
        "No folder selected",
        color=ft.Colors.WHITE_70,
        italic=True,
    )

    search_input = ft.TextField(
        hint_text="Write anything you remember from the file or its content.",
        hint_style=ft.TextStyle(color=ft.Colors.WHITE_70),
        color=ft.Colors.WHITE,
        focused_border_color="#55FFFFFF",
        expand=True,
    )

    output_column = ft.Column(spacing=10)

    folder_picker = ft.FilePicker()
    page.services.append(folder_picker)

    async def handle_click(e):
        nonlocal selected_folder_path

        try:
            path = await folder_picker.get_directory_path(
                dialog_title="Select Folder"
            )

            if path:
                selected_folder_path = path
                status_text.value = f"Selected Folder: {path}"
                status_text.color = ft.Colors.GREEN_400
            else:
                status_text.value = "No folder selected"
                status_text.color = ft.Colors.WHITE_70

        except Exception as ex:
            selected_folder_path = None
            status_text.value = f"Folder picker error: {ex}"
            status_text.color = ft.Colors.RED_ACCENT

        page.update()

    async def handle_submit(e):
        if not selected_folder_path:
            output_column.controls.clear()
            output_column.controls.append(
                ft.Text(
                    "Error: Please select a folder first!",
                    color=ft.Colors.RED_ACCENT,
                )
            )
            page.update()
            return

        user_text = (search_input.value or "").strip()

        if not user_text:
            output_column.controls.clear()
            output_column.controls.append(
                ft.Text(
                    "Error: Search field cannot be empty!",
                    color=ft.Colors.RED_ACCENT,
                )
            )
            page.update()
            return

        output_column.controls.clear()
        output_column.controls.append(
            ft.Text(
                f"⏳ Reading directory {selected_folder_path}...",
                color=ft.Colors.WHITE,
            )
        )
        page.update()

        scrubbed_files = await __import__("asyncio").to_thread(
            read_files,
            selected_folder_path,
        )

        output_column.controls.clear()
        output_column.controls.append(
            ft.Text(
                f"🤖 Processing {len(scrubbed_files)} scrubbed files...",
                color=ft.Colors.AMBER_ACCENT,
            )
        )
        page.update()

        analysis_result = await __import__("asyncio").to_thread(
            analyze_files_with_gemini,
            scrubbed_files,
            user_text,
        )

        output_column.controls.clear()

        output_column.controls.append(
            ft.Text(
                "🎯 Top System Meaning Matches Found:",
                size=16,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.GREEN_ACCENT,
            )
        )

        output_column.controls.append(
            ft.Text(
                analysis_result,
                color=ft.Colors.WHITE,
                selectable=True,
            )
        )

        paths_to_open = []

        for line in analysis_result.splitlines():
            path = line.strip()

            if path and os.path.isfile(path):
                paths_to_open.append(path)

        if paths_to_open:
            output_column.controls.append(
                ft.Text(
                    f"🚀 Opening top {min(5, len(paths_to_open))} matches...",
                    size=12,
                    color=ft.Colors.WHITE_60,
                )
            )

            for path in paths_to_open[:5]:
                try:
                    subprocess.Popen(["notepad.exe", path])
                except Exception:
                    pass
        else:
            output_column.controls.append(
                ft.Text(
                    "⚠️ No matching system files found.",
                    size=12,
                    color=ft.Colors.WHITE_60,
                )
            )

        page.update()

    about_dialog = ft.AlertDialog(
        title=ft.Text("About YF Official App"),
        content=ft.Text(
            "This app helps you find local files by describing their "
            "content or meaning. Sensitive data is filtered before "
            "information is sent to third-party LLMs."
        ),
        actions=[
            ft.TextButton(
                "Close",
                on_click=lambda e: page.close(about_dialog),
            )
        ],
    )

    page.appbar = ft.AppBar(
        title=ft.Text("YF Meaning Finder"),
        center_title=True,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions=[
            ft.IconButton(
                icon=ft.Icons.INFO_OUTLINED,
                tooltip="About this App",
                on_click=lambda e: page.open(about_dialog),
            )
        ],
    )

    page.decoration = ft.BoxDecoration(
        image=ft.DecorationImage(
            src="macos.jpg",
            fit=ft.BoxFit.COVER,
        )
    )

    top_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "YF Meaning Finder",
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                ),
                ft.Row(
                    controls=[
                        ft.TextButton(
                            "Select Folder",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=handle_click,
                            style=ft.ButtonStyle(
                                color=ft.Colors.WHITE,
                                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                            ),
                        ),
                        search_input,
                        ft.IconButton(
                            icon=ft.Icons.SEND,
                            icon_color=ft.Colors.WHITE,
                            tooltip="Submit Search",
                            bgcolor=ft.Colors.BLUE_ACCENT,
                            on_click=handle_submit,
                        ),
                    ],
                    spacing=20,
                ),
                status_text,
                ft.Divider(color="#22FFFFFF"),
                output_column,
            ],
            spacing=15,
        ),
        bgcolor="#33FFFFFF",
        blur=ft.Blur(15, 15),
        border=ft.Border.all(1, "#22FFFFFF"),
        border_radius=12,
        padding=20,
        margin=20,
    )

    page.add(top_card)


if __name__ == "__main__":
    ft.run(main)