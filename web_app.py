#!/usr/bin/env python3
import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from converter_logic import FileConverter

# --- Configuration ---
UPLOAD_FOLDER = 'web_uploads/'
CONVERTED_FOLDER = 'web_converted/'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

converter = FileConverter()


# --- Embedded browser UI ---
# Kept inline (rather than in templates/) so the project stays single-file
# for the web piece. The page hits the same /upload and /convert endpoints
# as any other client.
INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>File Converter</title>
<style>
  :root { color-scheme: light dark; }
  body {
    font-family: system-ui, -apple-system, sans-serif;
    max-width: 640px;
    margin: 2rem auto;
    padding: 0 1rem;
    line-height: 1.5;
  }
  h1 { margin-bottom: 0.25rem; }
  .sub { color: #777; margin-top: 0; }
  fieldset {
    border: 1px solid rgba(128,128,128,0.3);
    border-radius: 6px;
    padding: 1rem;
    margin-bottom: 1rem;
  }
  fieldset[disabled] { opacity: 0.5; }
  legend { font-weight: 600; padding: 0 0.4rem; }
  input[type=file], select {
    padding: 0.4rem;
    width: 100%;
    box-sizing: border-box;
    font-size: 1rem;
  }
  button {
    padding: 0.5rem 1.2rem;
    cursor: pointer;
    font-size: 1rem;
    border-radius: 4px;
    border: 1px solid rgba(128,128,128,0.4);
    background: rgba(99,102,241,0.12);
  }
  button:hover:not(:disabled) { background: rgba(99,102,241,0.22); }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  .status {
    padding: 0.6rem 0.8rem;
    margin-top: 0.6rem;
    border-radius: 4px;
    word-wrap: break-word;
  }
  .status.info { background: rgba(99,102,241,0.12); }
  .status.ok   { background: rgba(34,197,94,0.18); }
  .status.err  { background: rgba(239,68,68,0.18); color: #b91c1c; white-space: pre-wrap; }
  .footer { color: #888; font-size: 0.85rem; margin-top: 2rem; }
  .footer a { color: inherit; }
</style>
</head>
<body>
<h1>File Converter</h1>
<p class="sub">Upload a file, pick an output format, download the result.</p>

<fieldset>
  <legend>1. Choose a file</legend>
  <input type="file" id="file">
  <div id="upload-status"></div>
</fieldset>

<fieldset id="convert-step" disabled>
  <legend>2. Pick an output format</legend>
  <select id="target"></select>
  <p style="margin: 1rem 0 0;">
    <button id="convert" disabled>Convert</button>
  </p>
  <div id="convert-status"></div>
</fieldset>

<p class="footer">JSON API description at <a href="/api">/api</a>.</p>

<script>
const $ = id => document.getElementById(id);
let upload = null;

$('file').addEventListener('change', async e => {
  const file = e.target.files[0];
  if (!file) return;
  upload = null;
  $('target').innerHTML = '';
  $('convert').disabled = true;
  $('convert-step').setAttribute('disabled', '');
  $('convert-status').className = '';
  $('convert-status').textContent = '';
  setStatus('upload-status', 'Uploading…', 'info');

  const fd = new FormData();
  fd.append('file', file);
  try {
    const r = await fetch('/upload', { method: 'POST', body: fd });
    const data = await r.json();
    if (!r.ok || !data.success) throw new Error(data.error || 'Upload failed');
    upload = data;
    populateFormats(data);
    setStatus('upload-status', `Detected: ${data.input_format.toUpperCase()}`, 'ok');
    $('convert-step').removeAttribute('disabled');
    $('convert').disabled = false;
  } catch (err) {
    setStatus('upload-status', err.message, 'err');
  }
});

function populateFormats(data) {
  const sel = $('target');
  // Group by output format so duplicate-target engines sit adjacent.
  const byFmt = {};
  for (const [engine, formats] of Object.entries(data.output_options || {})) {
    for (const fmt of formats) {
      (byFmt[fmt] = byFmt[fmt] || []).push(engine);
    }
  }
  const preferred = data.preferred_engines || {};
  let firstPreferredValue = null;
  let firstAnyValue = null;
  Object.keys(byFmt).sort().forEach(fmt => {
    let engines = byFmt[fmt];
    const pref = preferred[fmt];
    if (pref && engines.includes(pref)) {
      engines = [pref, ...engines.filter(e => e !== pref)];
    }
    const multi = engines.length > 1;
    for (const engine of engines) {
      const opt = document.createElement('option');
      opt.value = `${engine}|${fmt}`;
      let label = `${fmt.toUpperCase()} (${engine})`;
      if (multi && engine === pref) {
        label += ' — preferred';
        if (firstPreferredValue === null) firstPreferredValue = opt.value;
      }
      opt.textContent = label;
      sel.appendChild(opt);
      if (firstAnyValue === null) firstAnyValue = opt.value;
    }
  });
  sel.value = firstPreferredValue || firstAnyValue || '';
}

$('convert').addEventListener('click', async () => {
  if (!upload) return;
  const choice = $('target').value;
  if (!choice) return;
  const [engine, output_format] = choice.split('|');
  setStatus('convert-status', 'Converting…', 'info');
  $('convert').disabled = true;
  try {
    const r = await fetch('/convert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input_filepath: upload.input_filepath,
        input_format: upload.input_format,
        output_format, engine,
      }),
    });
    const data = await r.json();
    if (!r.ok || !data.success) throw new Error(data.error || 'Conversion failed');
    const url = '/download/' + encodeURIComponent(data.download_filename);
    setStatus(
      'convert-status',
      `<a href="${url}">Download ${data.download_filename}</a>`,
      'ok',
      true,
    );
  } catch (err) {
    setStatus('convert-status', err.message, 'err');
  } finally {
    $('convert').disabled = false;
  }
});

function setStatus(id, msg, type, html=false) {
  const el = $(id);
  if (html) el.innerHTML = msg; else el.textContent = msg;
  el.className = 'status ' + type;
}
</script>
</body>
</html>
"""


# --- Routes ---
@app.route('/')
def index():
    return INDEX_HTML


@app.route('/api')
def api_description():
    """JSON description of the API endpoints for non-browser clients."""
    return jsonify({
        'service': 'File Converter API',
        'endpoints': {
            'POST /upload': 'multipart file upload; returns available output formats and preferred engines',
            'POST /convert': 'JSON {input_filepath, input_format, output_format, engine}',
            'GET /download/<filename>': 'fetch converted file',
        },
    })


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': 'No selected file'}), 400

    original_filename = secure_filename(file.filename)
    unique_id = str(uuid.uuid4())
    input_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{original_filename}")
    file.save(input_filepath)

    input_format = converter.detect_file_format(input_filepath)
    if not input_format:
        return jsonify({'success': False, 'error': 'Unsupported file type'}), 400

    return jsonify({
        'success': True,
        'input_filepath': input_filepath,
        'input_format': input_format,
        'output_options': converter.get_output_formats_grouped(input_format),
        # Map of output_format -> preferred engine for this input. The UI uses
        # this to mark the preferred entry and select it by default.
        'preferred_engines': converter.preferred_engines.get(input_format, {}),
    })


@app.route('/convert', methods=['POST'])
def convert_file_route():
    data = request.json or {}
    input_filepath = data.get('input_filepath')
    input_format = data.get('input_format')
    output_format = data.get('output_format')
    engine = data.get('engine')

    base_name = os.path.splitext(os.path.basename(input_filepath))[0]
    output_ext = converter.output_extensions.get(output_format, f'.{output_format}')
    output_filename = f"{base_name}_converted{output_ext}"
    output_filepath = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)

    success, message = converter.convert_file(
        input_filepath, output_filepath, input_format, output_format, engine
    )

    if success:
        return jsonify({
            'success': True,
            'download_filename': output_filename,
            'message': message,
        })
    return jsonify({'success': False, 'error': message}), 500


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['CONVERTED_FOLDER'], filename, as_attachment=True)
