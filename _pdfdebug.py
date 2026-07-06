import io, sys, logging
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
logging.basicConfig(level=logging.WARNING)

from datetime import date
from app import create_app
from app.pdf import _link_callback
from flask import render_template
from app.extensions import db
from app.models import Service

app = create_app()
with app.test_request_context("/pdf/service/1"):
    svc = db.session.get(Service, 1)
    html = render_template("print/pdf.html", services=[svc], car=svc.car,
                           owner=True, mode="owner", single=True, now=date.today())
    print("HTML length:", len(html))
    from xhtml2pdf import pisa
    out = io.BytesIO()
    try:
        status = pisa.CreatePDF(src=html, dest=out, link_callback=_link_callback, encoding="utf-8")
        print("status.err =", status.err)
        print("output bytes =", len(out.getvalue()))
    except Exception as e:
        import traceback; traceback.print_exc()
    # show link_callback resolutions
    print("static ->", _link_callback("/static/fonts/DejaVuSans.ttf", None))
    import os
    print("exists  ->", os.path.exists(_link_callback("/static/fonts/DejaVuSans.ttf", None)))
