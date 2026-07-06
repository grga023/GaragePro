"""Render HTML to PDF with xhtml2pdf (pure-Python friendly, works on the Pi).

A dedicated table-based template (print/pdf.html) is used because xhtml2pdf
supports only a subset of CSS (no flexbox). Serbian Latin glyphs are rendered
with a bundled DejaVu Sans font that is registered directly with ReportLab
(registering via CSS @font-face triggers a Windows temp-file lock bug).
"""
import io
import os

from flask import current_app

_FONTS_REGISTERED = False


def _register_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    fonts_dir = os.path.join(current_app.root_path, "static", "fonts")
    regular = os.path.join(fonts_dir, "DejaVuSans.ttf")
    bold = os.path.join(fonts_dir, "DejaVuSans-Bold.ttf")
    if os.path.exists(regular) and os.path.exists(bold):
        pdfmetrics.registerFont(TTFont("DejaVu", regular))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", bold))
        pdfmetrics.registerFontFamily(
            "DejaVu", normal="DejaVu", bold="DejaVu-Bold",
            italic="DejaVu", boldItalic="DejaVu-Bold",
        )
        _FONTS_REGISTERED = True


def _link_callback(uri, _rel):
    """Map /static/... and /media/... URLs to absolute filesystem paths."""
    if uri.startswith("/static/"):
        rel = uri[len("/static/"):]
        return os.path.join(current_app.root_path, "static", *rel.split("/"))
    if uri.startswith("/media/"):
        rel = uri[len("/media/"):]
        return os.path.join(current_app.config["UPLOAD_FOLDER"], *rel.split("/"))
    return uri


def render_pdf(html: str) -> bytes:
    from xhtml2pdf import pisa  # imported lazily so the app runs even if absent

    out = io.BytesIO()
    status = pisa.CreatePDF(src=html, dest=out,
                            link_callback=_link_callback, encoding="utf-8")
    if status.err:
        raise RuntimeError("Generisanje PDF-a nije uspelo.")
    return out.getvalue()
