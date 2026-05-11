"""
File Converter - Nautilus Extension
Filename: file_converter_extension.py

A Nautilus MenuProvider that adds a context-aware "Convert to ▸" submenu
to the right-click menu, listing only valid output formats for the
selected file(s). Conversions run in a background thread; results are
reported via desktop notifications.

Installed by symlinking into ~/.local/share/nautilus-python/extensions/
"""
import os
import sys
import threading
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse

import gi
# Support both Nautilus 3.x (GTK3) and 4.x (GTK4) hosts.
try:
    gi.require_version('Nautilus', '4.0')
except ValueError:
    gi.require_version('Nautilus', '3.0')
from gi.repository import Nautilus, GObject

# Follow the symlink back to the project directory so we can import the
# backend engine and locate gui.py for the "Open in File Converter…" item.
_EXT_DIR = os.path.dirname(os.path.realpath(__file__))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

from converter_logic import FileConverter

_converter = FileConverter()
_GUI_SCRIPT = os.path.join(_EXT_DIR, "gui.py")


def _path_from_file_info(file_info):
    """Return a local filesystem path for a Nautilus.FileInfo, or None if remote."""
    uri = file_info.get_uri()
    parsed = urlparse(uri)
    if parsed.scheme != 'file':
        return None
    return unquote(parsed.path)


def _notify(title, body, urgency='normal'):
    try:
        subprocess.run(
            ['notify-send', '-u', urgency, '-a', 'File Converter', title, body],
            check=False, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def _unique_output_path(input_file, output_format):
    base = Path(input_file).stem
    out_dir = os.path.dirname(input_file)
    ext = _converter.output_extensions.get(output_format, f'.{output_format}')
    candidate = os.path.join(out_dir, f"{base}{ext}")
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(out_dir, f"{base}_{counter}{ext}")
        counter += 1
    return candidate


def _run_conversion(files, output_format, engine):
    success = 0
    failures = []
    for f in files:
        input_format = _converter.detect_file_format(f)
        if not input_format:
            failures.append(f"{os.path.basename(f)}: unsupported")
            continue
        ok, msg = _converter.convert_file(
            f, _unique_output_path(f, output_format),
            input_format, output_format, engine,
        )
        if ok:
            success += 1
        else:
            short = msg.splitlines()[-1][:140] if msg else "unknown error"
            failures.append(f"{os.path.basename(f)}: {short}")

    total = len(files)
    if not failures:
        _notify("File Converter",
                f"Converted {success}/{total} file(s) to {output_format.upper()}.")
    else:
        body = f"Converted {success}/{total}.\n" + "\n".join(failures[:5])
        _notify("File Converter — errors", body, urgency='critical')


class FileConverterExtension(GObject.GObject, Nautilus.MenuProvider):
    def get_file_items(self, *args):
        # Nautilus 3.x calls (window, files); 4.x calls (files,). Last arg is always files.
        files = args[-1]
        if not files:
            return []

        local_files = []
        input_formats = set()
        for fi in files:
            if fi.is_directory():
                return []
            path = _path_from_file_info(fi)
            if path is None:
                return []
            fmt = _converter.detect_file_format(path)
            if fmt is None:
                return []
            local_files.append(path)
            input_formats.add(fmt)

        # Submenu only makes sense when all selected files share an input format.
        if not local_files or len(input_formats) != 1:
            return []
        input_format = next(iter(input_formats))

        output_options = _converter.get_output_formats_grouped(input_format)
        if not output_options:
            return []

        top = Nautilus.MenuItem(
            name='FileConverter::ConvertTo',
            label='Convert to',
            tip=f'Convert {input_format.upper()} → another format',
        )
        submenu = Nautilus.Menu()
        top.set_submenu(submenu)

        # Invert the engine→formats dict to format→[engines] so duplicate output
        # formats (e.g. PDF available via both Pandoc and LibreOffice) sit
        # adjacent in the menu. For each format, the preferred engine appears
        # first and gets a "— preferred" suffix.
        by_format: dict = {}
        for engine, formats in output_options.items():
            for fmt in formats:
                by_format.setdefault(fmt, []).append(engine)

        for fmt in sorted(by_format.keys()):
            engines = by_format[fmt]
            preferred = _converter.get_preferred_engine(input_format, fmt)
            if preferred in engines:
                engines = [preferred] + [e for e in engines if e != preferred]
            multi = len(engines) > 1
            for engine in engines:
                label = f'{fmt.upper()}  ({engine})'
                if multi and engine == preferred:
                    label += '  — preferred'
                item = Nautilus.MenuItem(
                    name=f'FileConverter::{engine}_{fmt}',
                    label=label,
                )
                item.connect('activate', self._on_format_selected,
                             local_files, fmt, engine)
                submenu.append_item(item)

        # Escape hatch: launch the full GUI for advanced cases
        # (e.g. markdown→PDF image-stripping prompt).
        gui_item = Nautilus.MenuItem(
            name='FileConverter::OpenGUI',
            label='Open in File Converter…',
            tip='Launch the full GUI with these files preloaded',
        )
        gui_item.connect('activate', self._on_open_gui, local_files)
        submenu.append_item(gui_item)

        return [top]

    def get_background_items(self, *args):
        return []

    def _on_format_selected(self, _item, files, output_format, engine):
        _notify("File Converter",
                f"Converting {len(files)} file(s) to {output_format.upper()}…")
        threading.Thread(
            target=_run_conversion,
            args=(files, output_format, engine),
            daemon=True,
        ).start()

    def _on_open_gui(self, _item, files):
        subprocess.Popen(
            ['python3', _GUI_SCRIPT, *files],
            start_new_session=True,
        )
