"""Production server using Waitress (pure Python, works on Windows and the Pi).

    python serve.py
Serves on 0.0.0.0:8000 by default (override with PORT / HOST env vars).
"""
import os

from waitress import serve

from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    threads = int(os.environ.get("THREADS", "4"))
    print(f"GaragePro pokrenut na http://{host}:{port}  (Ctrl+C za prekid)")
    serve(app, host=host, port=port, threads=threads)
