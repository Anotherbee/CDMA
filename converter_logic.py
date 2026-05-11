#!/usr/bin/env python3
"""
File Converter - Backend Logic
Filename: converter_logic.py
Contains the FileConverter class with all core conversion functionality,
decoupled from any user interface.
"""
import os
import json
import subprocess
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

class FileConverter:
    """
    Provides the core logic for file format detection and conversion.
    This class is UI-agnostic.
    """
    def __init__(self):
        """Initialize the conversion engine."""
        self.version = "5.4-GUI" # Version bump for the fix
        self.config_file = os.path.expanduser("~/.file_converter_config.json")
        self.config = self._load_config()
        self.preferred_engines = self._load_preferred_engines()

        # format definitions
        self.pandoc_formats = {
            'markdown': {'extensions': ['.md', '.markdown'], 'outputs': ['html', 'docx', 'odt', 'pdf', 'epub', 'rst', 'tex', 'txt']},
            'html': {'extensions': ['.html', '.htm'], 'outputs': ['markdown', 'docx', 'odt', 'pdf', 'epub', 'rst', 'tex', 'txt']},
            'docx': {'extensions': ['.docx'], 'outputs': ['markdown', 'html', 'odt', 'pdf', 'epub', 'rst', 'tex', 'txt']},
            'odt': {'extensions': ['.odt'], 'outputs': ['markdown', 'html', 'docx', 'pdf', 'epub', 'rst', 'tex', 'txt']},
            'epub': {'extensions': ['.epub'], 'outputs': ['markdown', 'html', 'docx', 'odt', 'pdf', 'rst', 'tex', 'txt']},
            'rst': {'extensions': ['.rst'], 'outputs': ['markdown', 'html', 'docx', 'odt', 'pdf', 'epub', 'tex', 'txt']},
            'tex': {'extensions': ['.tex'], 'outputs': ['markdown', 'html', 'docx', 'odt', 'pdf', 'epub', 'rst', 'txt']},
            'txt': {'extensions': ['.txt'], 'outputs': ['markdown', 'html', 'docx', 'odt', 'pdf', 'epub', 'rst', 'tex']}
        }
        self.libreoffice_formats = {
            'html': {'extensions': ['.html', '.htm'], 'outputs': ['pdf', 'docx', 'odt']},
            'doc': {'extensions': ['.doc'], 'outputs': ['pdf', 'docx', 'odt', 'rtf', 'txt', 'html']},
            'docx': {'extensions': ['.docx'], 'outputs': ['pdf', 'doc', 'odt', 'rtf', 'txt', 'html']},
            'odt': {'extensions': ['.odt'], 'outputs': ['pdf', 'doc', 'docx', 'rtf', 'txt', 'html']},
            'rtf': {'extensions': ['.rtf'], 'outputs': ['pdf', 'doc', 'docx', 'odt', 'txt', 'html']},
            'txt': {'extensions': ['.txt'], 'outputs': ['pdf', 'docx', 'odt', 'rtf', 'html']},
            'pdf': {'extensions': ['.pdf'], 'outputs': ['txt', 'html', 'docx', 'odt']},
            'ods': {'extensions': ['.ods'], 'outputs': ['pdf', 'xlsx', 'xls', 'csv']},
            'xls': {'extensions': ['.xls'], 'outputs': ['pdf', 'xlsx', 'ods', 'csv']},
            'xlsx': {'extensions': ['.xlsx'], 'outputs': ['pdf', 'xls', 'ods', 'csv']},
            'odp': {'extensions': ['.odp'], 'outputs': ['pdf', 'pptx', 'ppt']},
            'ppt': {'extensions': ['.ppt'], 'outputs': ['pdf', 'pptx', 'odp']},
            'pptx': {'extensions': ['.pptx'], 'outputs': ['pdf', 'ppt', 'odp']}
        }
        self.ffmpeg_formats = {
            'mp3': {'extensions': ['.mp3'], 'outputs': ['wav', 'flac', 'ogg', 'aac', 'm4a']},
            'wav': {'extensions': ['.wav'], 'outputs': ['mp3', 'flac', 'ogg', 'aac', 'm4a']},
            'flac': {'extensions': ['.flac'], 'outputs': ['mp3', 'wav', 'ogg', 'aac', 'm4a']},
            'm4a': {'extensions': ['.m4a'], 'outputs': ['mp3', 'wav', 'flac', 'ogg', 'aac']},
            'mp4': {'extensions': ['.mp4', '.m4v'], 'outputs': ['avi', 'mkv', 'webm', 'gif', 'mp3', 'wav']},
            'mkv': {'extensions': ['.mkv'], 'outputs': ['mp4', 'avi', 'webm', 'gif', 'mp3', 'wav']},
            'avi': {'extensions': ['.avi'], 'outputs': ['mp4', 'mkv', 'webm', 'gif', 'mp3', 'wav']},
            'jpg': {'extensions': ['.jpg', '.jpeg'], 'outputs': ['png', 'webp', 'gif', 'bmp']},
            'png': {'extensions': ['.png'], 'outputs': ['jpg', 'webp', 'gif', 'bmp']},
            'webp': {'extensions': ['.webp'], 'outputs': ['jpg', 'png', 'gif']},
            'svg': {'extensions': ['.svg'], 'outputs': ['png', 'jpg', 'pdf']}
        }
        
        self.pandoc_format_mapping = {'tex': 'latex', 'markdown': 'markdown', 'html': 'html', 'docx': 'docx', 'odt': 'odt', 'epub': 'epub', 'rst': 'rst', 'pdf': 'pdf'}
        self.libreoffice_format_mapping = {'txt': 'txt', 'doc': 'doc', 'docx': 'docx', 'odt': 'odt', 'rtf': 'rtf', 'pdf': 'pdf', 'html': 'html', 'ods': 'ods', 'xls': 'xls', 'xlsx': 'xlsx', 'csv': 'csv', 'odp': 'odp', 'ppt': 'ppt', 'pptx': 'pptx'}
        
        self.output_extensions = {
            'markdown': '.md', 'html': '.html', 'docx': '.docx', 'odt': '.odt', 'pdf': '.pdf', 'epub': '.epub', 'rst': '.rst', 'tex': '.tex', 'txt': '.txt', 'doc': '.doc', 'rtf': '.rtf', 'ods': '.ods', 'xls': '.xls', 'xlsx': '.xlsx', 'csv': '.csv', 'odp': '.odp', 'ppt': '.ppt', 'pptx': '.pptx',
            'mp3': '.mp3', 'wav': '.wav', 'flac': '.flac', 'ogg': '.ogg', 'aac': '.aac', 'm4a': '.m4a',
            'mp4': '.mp4', 'avi': '.avi', 'mkv': '.mkv', 'webm': '.webm', 'gif': '.gif',
            'jpg': '.jpg', 'png': '.png', 'webp': '.webp', 'bmp': '.bmp', 'svg': '.svg'
        }

    def _load_config(self) -> Dict:
        default_config = {'last_output_dir': os.path.expanduser("~")}
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f: config = json.load(f)
                if not os.path.exists(config.get('last_output_dir', '')): config['last_output_dir'] = default_config['last_output_dir']
                return config
        except Exception: pass
        return default_config

    def _load_preferred_engines(self) -> Dict[str, Dict[str, str]]:
        """Load (input_format, output_format) -> engine preferences from JSON."""
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'preferred_engines.json')
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            # Ignore any non-dict entries (e.g. the "_comment" key).
            return {k: v for k, v in data.items() if isinstance(v, dict)}
        except Exception:
            return {}

    def get_preferred_engine(self, input_format: str, output_format: str) -> str | None:
        """Return the preferred engine for this conversion, or None if no preference is set."""
        return self.preferred_engines.get(input_format, {}).get(output_format)

    def save_config(self):
        try:
            with open(self.config_file, 'w') as f: json.dump(self.config, f, indent=2)
        except Exception: pass

    def get_output_formats_grouped(self, input_format: str) -> Dict[str, List[str]]:
        grouped = {'Pandoc': [], 'LibreOffice': [], 'FFmpeg': []}
        if input_format in self.pandoc_formats: grouped['Pandoc'] = self.pandoc_formats[input_format]['outputs']
        if input_format in self.libreoffice_formats: grouped['LibreOffice'] = self.libreoffice_formats[input_format]['outputs']
        if input_format in self.ffmpeg_formats: grouped['FFmpeg'] = self.ffmpeg_formats[input_format]['outputs']
        return {k: v for k, v in grouped.items() if v}

    def detect_file_format(self, filename: str) -> str | None:
        ext = Path(filename).suffix.lower()
        all_formats = {**self.pandoc_formats, **self.libreoffice_formats, **self.ffmpeg_formats}
        for format_name, format_info in all_formats.items():
            if ext in format_info['extensions']: return format_name
        return None

    def run_image_diagnostic(self, markdown_file: str) -> Dict:
        try:
            with open(markdown_file, 'r', encoding='utf-8') as f: content = f.read()
            base64_images = re.findall(r'data:image/[^)]*', content)
            file_size = os.path.getsize(markdown_file)
            return {'base64_count': len(base64_images), 'file_size': file_size, 'is_problematic': len(base64_images) > 0 or file_size > 500000}
        except Exception as e: return {'error': str(e)}

    def convert_file(self, input_file: str, output_file: str, input_format: str,
                     output_format: str, engine: str, remove_images: bool = False) -> Tuple[bool, str]:
        actual_input = input_file
        temp_file = None
        try:
            # Pre-process to remove problematic images for both Markdown and HTML
            if (input_format == 'markdown' and remove_images) or (engine == 'Pandoc' and input_format == 'html'):
                with open(input_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Regex to remove markdown images and html img tags
                content = re.sub(r'!\[.*?\]\([^)]*\)|<img[^>]*>|<figure>.*?</figure>', '[IMAGE REMOVED]', content, flags=re.DOTALL)
                
                # Use a temporary file with the correct extension
                suffix = '.md' if input_format == 'markdown' else '.html'
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8')
                temp_file.write(content)
                temp_file.close()
                actual_input = temp_file.name

            cmd = []
            if engine == 'Pandoc':
                pandoc_input = self.pandoc_format_mapping.get(input_format)
                pandoc_output = self.pandoc_format_mapping.get(output_format, output_format)
                cmd = ['pandoc']
                if pandoc_input: cmd.extend(['-f', pandoc_input])
                cmd.extend(['-t', pandoc_output, '-o', output_file, actual_input])
                if output_format == 'pdf': cmd.insert(1, '--pdf-engine=xelatex')
            elif engine == 'LibreOffice':
                lo_output = self.libreoffice_format_mapping.get(output_format, output_format)
                output_dir = os.path.dirname(output_file)
                cmd = ['libreoffice', '--headless']
                if input_format == 'pdf':
                    cmd.extend(['--infilter', 'writer_pdf_import'])
                cmd.extend(['--convert-to', lo_output, '--outdir', output_dir, actual_input])
            elif engine == 'FFmpeg':
                cmd = ['ffmpeg', '-i', actual_input, '-y', output_file]

            if not cmd: return False, f"Unknown engine: {engine}"
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                if engine == 'LibreOffice' and not os.path.exists(output_file):
                    expected_ext = self.output_extensions.get(output_format, f'.{output_format}')
                    base_name = Path(input_file).stem
                    generated_file = os.path.join(output_dir, f"{base_name}{expected_ext}")
                    if os.path.exists(generated_file): os.rename(generated_file, output_file)
                    else: return False, "LibreOffice conversion failed: Output file not found."
                return True, f"Successfully converted to {os.path.basename(output_file)}"
            else:
                if "xelatex not found" in result.stderr:
                    return False, f"Conversion failed.\n\nEngine: Pandoc\nError: PDF Engine 'xelatex' not found. Please install it with:\nsudo apt install texlive-xetex"
                return False, f"Conversion failed.\n\nEngine: {engine}\nError: {result.stderr}"
        except subprocess.TimeoutExpired: return False, "Conversion timed out after 120 seconds."
        except Exception as e: return False, f"An unexpected error occurred: {e}"
        finally:
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)