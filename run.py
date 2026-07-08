"""Development server (auto-reload, debug). For testing on Windows.

    python run.py
Then open http://127.0.0.1:8000
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Tesseract OCR — must be set before any child process or import
if 'TESSDATA_PREFIX' not in os.environ:
    os.environ['TESSDATA_PREFIX'] = r"C:\Program Files\Tesseract-OCR\tessdata"

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
