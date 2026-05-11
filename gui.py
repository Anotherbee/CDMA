#!/usr/bin/env python3
"""
File Converter - GUI Frontend
Filename: gui.py
A GTK-based graphical user interface for the File Converter application.
"""
import sys
import os
import threading
from pathlib import Path

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gio

from converter_logic import FileConverter

class FileConverterWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.converter = FileConverter()
        self.input_files = []

        self.set_title("File Converter")
        self.set_default_size(500, 400)
        self.set_border_width(10)

        header = Gtk.HeaderBar(title="File Converter", show_close_button=True)
        self.set_titlebar(header)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        self.select_button = Gtk.Button(label="Select File(s) to Convert...")
        vbox.pack_start(self.select_button, False, True, 0)

        self.info_label = Gtk.Label(label="Select one or more files to begin.", xalign=0)
        vbox.pack_start(self.info_label, False, True, 0)

        options_frame = Gtk.Frame(label="Conversion Options")
        vbox.pack_start(options_frame, False, True, 10)
        
        options_grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=10)
        options_frame.add(options_grid)

        output_format_label = Gtk.Label(label="Output Format:", xalign=0)
        self.output_format_combo = Gtk.ComboBoxText()
        options_grid.attach(output_format_label, 0, 0, 1, 1)
        options_grid.attach(self.output_format_combo, 1, 0, 1, 1)

        self.convert_button = Gtk.Button(label="Convert")
        self.convert_button.set_sensitive(False)
        vbox.pack_start(self.convert_button, False, True, 0)

        self.progress_bar = Gtk.ProgressBar()
        vbox.pack_start(self.progress_bar, False, True, 5)

        self.select_button.connect("clicked", self.on_select_files_clicked)
        self.convert_button.connect("clicked", self.on_convert_clicked)
        
        self.show_all()

    def on_select_files_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a file",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        dialog.set_select_multiple(True)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.input_files = dialog.get_filenames()
            self.update_ui_after_selection()
        
        dialog.destroy()

    def update_ui_after_selection(self):
        if not self.input_files:
            self.info_label.set_text("Select one or more files to begin.")
            self.info_label.set_tooltip_text(None)
            self.convert_button.set_sensitive(False)
            return

        # CORRECTED: Add a tooltip to show the list of selected files.
        filenames = [os.path.basename(f) for f in self.input_files]
        self.info_label.set_tooltip_text("\n".join(filenames))

        if len(self.input_files) == 1:
            self.info_label.set_text(f"Selected: {filenames[0]}")
        else:
            self.info_label.set_text(f"Selected: {len(self.input_files)} files")

        self.populate_output_formats()

    def populate_output_formats(self):
        self.output_format_combo.remove_all()
        first_file = self.input_files[0]
        input_format = self.converter.detect_file_format(first_file)

        if not input_format:
            self.show_dialog(Gtk.MessageType.ERROR, "Unsupported File Type", 
                             f"The format of '{os.path.basename(first_file)}' is not supported.")
            self.convert_button.set_sensitive(False)
            return

        output_options = self.converter.get_output_formats_grouped(input_format)
        if not output_options:
            self.show_dialog(Gtk.MessageType.ERROR, "No Conversions Available", 
                             f"No output formats are available for '{input_format}' files.")
            self.convert_button.set_sensitive(False)
            return

        # Group by output format so duplicate-target engines sit adjacent, with
        # the preferred engine first and tagged "— preferred" when there is a
        # choice. Mirrors the Nautilus right-click submenu.
        by_format: dict = {}
        for engine, formats in output_options.items():
            for fmt in formats:
                by_format.setdefault(fmt, []).append(engine)

        first_id = None
        preferred_id = None
        for fmt in sorted(by_format.keys()):
            engines = by_format[fmt]
            preferred = self.converter.get_preferred_engine(input_format, fmt)
            if preferred in engines:
                engines = [preferred] + [e for e in engines if e != preferred]
            multi = len(engines) > 1
            for engine in engines:
                label = f"{fmt.upper()} (using {engine})"
                if multi and engine == preferred:
                    label += " — preferred"
                combo_id = f"{engine}|{fmt}"
                self.output_format_combo.append(combo_id, label)
                if first_id is None:
                    first_id = combo_id
                if preferred_id is None and engine == preferred and multi:
                    preferred_id = combo_id

        self.output_format_combo.set_active_id(preferred_id or first_id)
        self.convert_button.set_sensitive(True)

    def on_convert_clicked(self, widget):
        active_id = self.output_format_combo.get_active_id()
        if not active_id: return
        
        engine, output_format = active_id.split('|')
        input_format = self.converter.detect_file_format(self.input_files[0])
        
        if input_format == 'markdown' and output_format == 'pdf':
            diag = self.converter.run_image_diagnostic(self.input_files[0])
            if diag.get('is_problematic'):
                dialog = Gtk.MessageDialog(
                    transient_for=self, modal=True, message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.NONE, text="Potential Issue Detected")
                dialog.format_secondary_text(
                    f"This Markdown file may contain problematic images or is very large. "
                    "It's recommended to convert with images removed to prevent errors."
                )
                dialog.add_buttons(
                    "Cancel", Gtk.ResponseType.CANCEL, "Convert Anyway", Gtk.ResponseType.NO,
                    "_Remove Images & Convert", Gtk.ResponseType.YES)
                response = dialog.run()
                dialog.destroy()

                if response == Gtk.ResponseType.CANCEL: return
                remove_images = (response == Gtk.ResponseType.YES)
                self.start_conversion_thread(output_format, engine, remove_images)
            else:
                self.start_conversion_thread(output_format, engine)
        else:
            self.start_conversion_thread(output_format, engine)

    def start_conversion_thread(self, output_format, engine, remove_images=False):
        self.set_ui_busy(True)
        thread = threading.Thread(
            target=self.conversion_worker,
            args=(self.input_files, output_format, engine, remove_images))
        thread.daemon = True
        thread.start()

    def conversion_worker(self, files, output_format, engine, remove_images):
        total = len(files)
        success_count = 0
        errors = []
        for i, input_file in enumerate(files):
            GLib.idle_add(self.progress_bar.set_fraction, (i + 1) / total)
            input_format = self.converter.detect_file_format(input_file)
            base_name = Path(input_file).stem
            output_dir = os.path.dirname(input_file)
            output_ext = self.converter.output_extensions.get(output_format, f'.{output_format}')
            output_file = os.path.join(output_dir, f"{base_name}{output_ext}")
            counter = 1
            while os.path.exists(output_file):
                output_file = os.path.join(output_dir, f"{base_name}_{counter}{output_ext}")
                counter += 1
            success, message = self.converter.convert_file(
                input_file, output_file, input_format, output_format, engine, remove_images)
            if success: success_count += 1
            else: errors.append(f"{os.path.basename(input_file)}: {message}")
        GLib.idle_add(self.on_conversion_finished, success_count, total, errors)

    def on_conversion_finished(self, success_count, total_files, errors):
        self.set_ui_busy(False)
        if not errors:
            self.show_dialog(Gtk.MessageType.INFO, "Conversion Complete", 
                             f"Successfully converted {success_count} of {total_files} file(s).")
        else:
            error_details = "\n".join(errors)
            self.show_dialog(Gtk.MessageType.ERROR, f"Conversion Finished with Errors",
                             f"Successfully converted {success_count} of {total_files} file(s).\n\nErrors:\n{error_details}")
        self.progress_bar.set_fraction(0)

    def set_ui_busy(self, busy):
        self.convert_button.set_sensitive(not busy)
        self.select_button.set_sensitive(not busy)
        self.output_format_combo.set_sensitive(not busy)
        if busy: self.progress_bar.pulse()
        else: self.progress_bar.set_fraction(0)

    def show_dialog(self, msg_type, title, text):
        dialog = Gtk.MessageDialog(
            transient_for=self, modal=True, message_type=msg_type,
            buttons=Gtk.ButtonsType.OK, text=title)
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()
        
    def load_files_from_args(self, files):
        self.input_files = [f for f in files if os.path.exists(f)]
        if self.input_files:
            GLib.idle_add(self.update_ui_after_selection)


class FileConverterApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="com.cmda.fileconverter", 
                         flags=Gio.ApplicationFlags.HANDLES_OPEN, **kwargs)
        self.window = None

    def do_activate(self):
        if not self.window: self.window = FileConverterWindow(application=self)
        self.window.present()

    def do_open(self, files, n_files, hint):
        if not self.window: self.window = FileConverterWindow(application=self)
        self.window.load_files_from_args([f.get_path() for f in files])
        self.window.present()


if __name__ == "__main__":
    app = FileConverterApp()
    app.run(sys.argv)