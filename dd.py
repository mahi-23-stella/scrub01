import os
import subprocess
import json
from flask import Flask, render_template, request

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"

# Ensure the uploads directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index1():
    """Render the upload form."""
    return render_template('index1.html')

@app.route('/submit', methods=['POST'])
def submit():
    """Handles file upload, runs `app2.py`, and displays extracted tables."""
    if 'pdf_file' not in request.files:
        return "Error: No file uploaded", 400

    pdf_file = request.files['pdf_file']
    if pdf_file.filename == '':
        return "Error: No file selected", 400

    pdf_path = os.path.join(UPLOAD_FOLDER, pdf_file.filename)

    try:
        pdf_file.save(pdf_path)  # Save uploaded PDF

        # Run `app2.py` and capture JSON output
        result = subprocess.run(["python", "dd1.py", pdf_path], capture_output=True, text=True)

        # ✅ Debugging: Print raw output from app2.py
        print("Raw Output from dd1.py:", result.stdout)

        if result.returncode == 0:
            try:
                extracted_data = json.loads(result.stdout)  # ✅ Ensure JSON output
            except json.JSONDecodeError:
                extracted_data = {"error": "Invalid JSON returned from dd1.py"}
        else:
            extracted_data = {"error": result.stderr}

    except Exception as e:
        extracted_data = {"error": str(e)}

    return render_template('result1.html', extracted_data=extracted_data)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)