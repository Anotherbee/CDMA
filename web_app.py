#!/usr/bin/env python3
import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import uuid # To generate unique filenames and avoid conflicts

# Import your existing, unaltered converter logic
from converter_logic import FileConverter

# --- Configuration ---
UPLOAD_FOLDER = 'web_uploads/'
CONVERTED_FOLDER = 'web_converted/'
ALLOWED_EXTENSIONS = {'txt', 'md', 'html', 'docx', 'odt', 'pdf', 'pptx', 'mp4', 'mp3', 'jpg', 'png'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

# Instantiate your converter ONCE
converter = FileConverter()

# --- Root Route ---
# No HTML frontend ships with this project — the GTK app (gui.py) is the
# primary UI. The root route returns a JSON description of the API so callers
# (curl, scripts, future SPAs) can discover the endpoints.
@app.route('/')
def index():
    return jsonify({
        'service': 'File Converter API',
        'endpoints': {
            'POST /upload': 'multipart file upload; returns available output formats',
            'POST /convert': 'JSON {input_filepath, input_format, output_format, engine}',
            'GET /download/<filename>': 'fetch converted file',
        },
    })

# --- API Routes ---
@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles file upload and returns available conversion formats."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        # Save the file with a unique ID to prevent overwrites
        original_filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        input_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{original_filename}")
        file.save(input_filepath)

        # Use your existing logic to get formats
        input_format = converter.detect_file_format(input_filepath)
        if not input_format:
            return jsonify({'error': 'Unsupported file type'}), 400
        
        output_options = converter.get_output_formats_grouped(input_format)

        return jsonify({
            'success': True,
            'input_filepath': input_filepath,
            'input_format': input_format,
            'output_options': output_options
        })

@app.route('/convert', methods=['POST'])
def convert_file_route():
    """Handles the conversion request."""
    data = request.json
    input_filepath = data.get('input_filepath')
    input_format = data.get('input_format')
    output_format = data.get('output_format')
    engine = data.get('engine')

    # Generate a unique output path
    base_name = os.path.splitext(os.path.basename(input_filepath))[0]
    output_ext = converter.output_extensions.get(output_format, f'.{output_format}')
    output_filename = f"{base_name}_converted{output_ext}"
    output_filepath = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

    # Use your existing conversion logic
    success, message = converter.convert_file(
        input_filepath, output_filepath, input_format, output_format, engine
    )

    if success:
        return jsonify({
            'success': True,
            'download_filename': output_filename,
            'message': message
        })
    else:
        return jsonify({'success': False, 'error': message}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Serves the converted file for download."""
    return send_from_directory(app.config['CONVERTED_FOLDER'], filename, as_attachment=True)
