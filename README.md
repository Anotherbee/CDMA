# File Converter

A universal file conversion utility for Debian/GNOME with a GTK GUI, a context-aware Nautilus right-click submenu, and an optional Flask web API. Wraps Pandoc, LibreOffice, and FFmpeg behind a single, consistent interface.

**Version:** 5.5
**Platform:** Debian-based Linux with GNOME (Nautilus 3 or 4)

## What it does

Converts documents, spreadsheets, presentations, images, audio, and video between formats. Three engines are wired in:

| Engine      | Best for                                                              |
|-------------|-----------------------------------------------------------------------|
| Pandoc      | Markup (markdown, rst, tex, html, epub) and clean text-oriented output |
| LibreOffice | Office docs (docx, odt, rtf, ppt, xls); PDF rendering with layout fidelity |
| FFmpeg      | Audio, video, and raster image conversion                              |

When more than one engine can produce the same target (e.g. DOCX → PDF), the recommended engine is marked in the menus. The recommendation is fully overridable — see [Configuration](#configuration).

## Features

- **Native GTK GUI** with file picker, format dropdown, and progress feedback.
- **Nautilus right-click integration** in two layers:
  - A context-aware `Convert to ▸` submenu (via `nautilus-python`) that lists only valid output formats for the selected file(s), marks the preferred engine, and runs conversions headlessly with desktop notifications.
  - A `Scripts → Convert with File Converter` fallback that launches the full GUI with files preloaded.
- **Configurable engine preferences** via a JSON file you can edit at any time.
- **Markdown → PDF image diagnostics** that warn before converting Markdown with embedded base64 images or very large files, with a one-click option to strip them.
- **HTML pre-processing** that removes broken `<img>` / `<figure>` tags before Pandoc conversion.
- **Optional Flask web API** for headless / programmatic use.

## Project layout

| File                            | Role                                                  |
|---------------------------------|-------------------------------------------------------|
| `converter_logic.py`            | UI-agnostic `FileConverter` engine and format tables  |
| `gui.py`                        | GTK desktop application                               |
| `file_converter_extension.py`   | `Nautilus.MenuProvider` (the context-aware submenu)   |
| `web_app.py`                    | Flask API (upload / convert / download)               |
| `preferred_engines.json`        | Engine preference map; edit to change defaults        |
| `setup_gui.sh`                  | Installer: Nautilus integration, desktop entry, CLI   |
| `test_gui.sh`                   | Verification test suite                               |
| `CMDA - GUI Evolution.txt`      | v5.5 release notes                                    |

## Installation

1. **Clone the repository** to a stable location. The setup script wires symlinks back to this directory, so if you move it later you'll need to re-run setup.
   ```bash
   git clone https://github.com/Anotherbee/CDMA.git ~/file_converter
   cd ~/file_converter
   ```

2. **Install system dependencies:**
   ```bash
   sudo apt update
   sudo apt install -y \
       pandoc libreoffice ffmpeg texlive-xetex \
       python3 python3-gi gir1.2-gtk-3.0 python3-nautilus \
       zenity libnotify-bin
   ```
   The web API additionally needs Flask: `pip install flask`.

3. **Run the setup script.** It installs the Nautilus right-click script and extension, a desktop launcher, MIME associations, and a `file-converter` command-line link:
   ```bash
   ./setup_gui.sh
   ```

4. **Restart Nautilus** so the extension loads:
   ```bash
   nautilus -q
   ```

5. *(Optional)* **Verify:**
   ```bash
   ./test_gui.sh
   ```

## Usage

### Right-click submenu (fastest)
In Nautilus, right-click any file (or multi-select files that share an input format) and choose `Convert to ▸`. The submenu shows only valid output formats; the preferred engine is suffixed with `— preferred` when there is a choice. Conversion runs in the background and a desktop notification reports completion.

If your selection spans mixed input formats, the submenu hides itself — use the `Scripts → Convert with File Converter` fallback. To use the markdown→PDF image-stripping prompt, pick `Open in File Converter…` at the bottom of the submenu.

### Application launcher
Press `Super`, search for **File Converter**, launch. Pick files, choose an output format, click Convert.

### Command line
```bash
file-converter                          # launch GUI, empty
file-converter path/to/doc.docx         # launch GUI with one file preloaded
file-converter doc1.docx doc2.docx ...  # multi-file
```

### Web API
Start the Flask server:
```bash
python3 -m flask --app web_app run
```

| Endpoint                    | Behavior                                                       |
|-----------------------------|----------------------------------------------------------------|
| `GET /`                     | JSON description of the API                                    |
| `POST /upload`              | Multipart upload; returns available output formats by engine   |
| `POST /convert`             | JSON `{input_filepath, input_format, output_format, engine}`   |
| `GET /download/<filename>`  | Fetch the converted file                                       |

Uploaded files land in `web_uploads/`; converted output in `web_converted/`. Both are created on first run.

## Configuration

### Engine preferences
`preferred_engines.json` selects the recommended engine when more than one can produce the same target. Nested map of `input_format → output_format → engine`:

```json
{
  "docx": {
    "pdf":  "LibreOffice",
    "odt":  "LibreOffice",
    "html": "Pandoc",
    "txt":  "Pandoc"
  }
}
```

Valid engine names: `"Pandoc"`, `"LibreOffice"`, `"FFmpeg"`. Any `_comment` keys or non-dict values are ignored, so you can leave inline notes. Conversions where only one engine applies are picked automatically and don't need an entry.

Defaults that ship in the file:
- **Office docs → PDF** and **DOCX↔ODT round-trip**: LibreOffice (layout fidelity).
- **Office docs → HTML / TXT**: Pandoc (semantic output, clean text extraction).
- **TXT → anything** and **HTML → DOCX/ODT**: Pandoc.

After editing, restart Nautilus (`nautilus -q`) so the extension re-reads the file. The GTK GUI picks up changes on next launch.

### Per-user state
`~/.file_converter_config.json` stores the last-used output directory.

## Supported formats

- **Documents (Pandoc):** markdown, html, docx, odt, epub, rst, tex, txt, pdf (output).
- **Office (LibreOffice):** doc, docx, odt, rtf, txt, html, pdf (in/out); ods, xls, xlsx, csv; odp, ppt, pptx.
- **Audio (FFmpeg):** mp3, wav, flac, m4a, ogg, aac.
- **Video (FFmpeg):** mp4, mkv, avi, webm, gif.
- **Images (FFmpeg):** jpg, png, webp, gif, bmp, svg.

Multi-hop conversions (e.g. RTF → EPUB via DOCX) are not chained automatically — you have to do them in two steps.

## Uninstall

```bash
./setup_gui.sh --uninstall
```
Removes the Nautilus script, the right-click extension symlink, the desktop entry, the MIME associations, and the `file-converter` command. Source files and `~/.file_converter_config.json` are left alone.

## Limitations

- Single-hop conversions only — no graph search across engines.
- The right-click submenu hides itself for mixed-format selections; fall back to the GUI script.
- Per-file conversion timeout of 120 seconds (set in `convert_file()`).
- Right-click integration is GNOME/Nautilus only. KDE / XFCE get the desktop entry and CLI but no right-click menu.
