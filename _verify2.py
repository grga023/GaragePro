import io, re, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from app import create_app

app = create_app()
c = app.test_client()

ok = True
def check(label, cond):
    global ok; ok = ok and cond
    print(("PASS" if cond else "FAIL"), "-", label)

def token(path):
    html = c.get(path).get_data(as_text=True)
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return m.group(1) if m else None

# --- CSRF ---
t = token("/login")
check("login page exposes csrf token", bool(t))
r = c.post("/login", data={"username": "admin", "password": "admin123"})
check("POST /login WITHOUT token is blocked (400)", r.status_code == 400)
r = c.post("/login", data={"username": "admin", "password": "admin123", "csrf_token": t},
           follow_redirects=True)
check("login WITH token works", r.status_code == 200 and "Odjava" in r.get_data(as_text=True))

# --- Pages (incl. new ones) ---
for p in ["/", "/services", "/cars", "/car/1", "/service/1", "/reports",
          "/analytics", "/users", "/setup", "/backup"]:
    check("GET %s" % p, c.get(p).status_code == 200)

# --- Charts ---
html = c.get("/analytics").get_data(as_text=True)
check("analytics embeds chartData + Chart.js + analytics.js",
      'id="chartData"' in html and "chart.umd.min.js" in html and "analytics.js" in html)

# --- Dark theme assets ---
home = c.get("/").get_data(as_text=True)
check("dark-theme toggle + theme.js present",
      'id="themeToggle"' in home and "theme.js" in home and 'data-bs-theme' in home)

# --- Security headers ---
h = c.get("/").headers
check("security headers set",
      h.get("X-Content-Type-Options") == "nosniff" and "Content-Security-Policy" in h)

# --- Upload a logo (validates image path used by PDF) ---
from PIL import Image
def png():
    b = io.BytesIO(); Image.new("RGB", (400, 200), (10, 40, 90)).save(b, "PNG"); b.seek(0); return b
st = token("/setup")
c.post("/setup", data={"name": "Auto Servis Test", "address": "Adresa 1",
                       "contact": "021/000", "csrf_token": st,
                       "logo": (png(), "logo.png")},
       content_type="multipart/form-data", follow_redirects=True)

# --- PDF export ---
for p in ["/pdf/service/1?mode=customer", "/pdf/service/1?mode=owner",
          "/pdf/car/1?mode=customer", "/pdf/car/1?mode=owner"]:
    r = c.get(p); body = r.get_data()
    check("PDF %s -> valid %%PDF" % p,
          r.status_code == 200 and r.mimetype == "application/pdf" and body[:4] == b"%PDF")
# Serbian font actually embedded (DejaVu) so č/ć/đ render:
owner_pdf = c.get("/pdf/service/1?mode=owner").get_data()
check("PDF embeds DejaVu font (Serbian glyphs)", b"DejaVu" in owner_pdf)

# --- Backups ---
bt = token("/backup")
r = c.post("/backup/create", data={"csrf_token": bt}, follow_redirects=True)
check("create backup", r.status_code == 200 and "napravljena" in r.get_data(as_text=True))
m = re.search(r"(backup_\d{8}_\d{6}\.zip)", c.get("/backup").get_data(as_text=True))
check("backup listed", bool(m))
if m:
    r = c.get("/backup/download/" + m.group(1))
    check("download backup zip", r.status_code == 200)
    # verify zip contains db + uploads
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(r.get_data()))
    names = z.namelist()
    check("backup contains carservice.db", "carservice.db" in names)
    check("backup contains uploads", any(n.startswith("uploads/") for n in names))
# path traversal guard
check("backup download rejects bad name", c.get("/backup/download/..%2f..%2fconfig.py").status_code in (400, 404))

# --- CSRF-protected service create + mileage recompute ---
ft = token("/service/new?car_id=1")
r = c.post("/service/new?car_id=1", data={
    "csrf_token": ft, "car_id": "1", "date": "2026-07-05", "mileage": "150000",
    "labor_price": "1000", "part_name[]": "Filter X", "part_qty[]": "1",
    "part_price[]": "100", "part_disc[]": "50"}, follow_redirects=True)
check("create service (CSRF) works", r.status_code == 200 and "Filter X" in r.get_data(as_text=True))
carhtml = c.get("/car/1").get_data(as_text=True)
check("car mileage updated to 150.000", "150.000" in carhtml)

print("\nRESULT:", "ALL PASS" if ok else "SOME FAILED")
