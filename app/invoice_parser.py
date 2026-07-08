"""Parse invoice images/PDFs via OCR and extract parts table.

Supports:
  - PDF files (rendered to image via pypdfium2)
  - Image files (JPEG, PNG, etc.)

Uses Tesseract OCR. Parses the standard Serbian auto-parts invoice format:
  RB | Kataloski br. | Opis | ... | Kolicina | JM | Jedinicna cena | Prod. cena | Iznos
"""
import io
import os
import re
import logging

from PIL import Image

log = logging.getLogger(__name__)

# Tesseract config — set env var BEFORE pytesseract is ever imported
TESSERACT_CMD = os.environ.get(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
# Use LOCAL tessdata copy — avoids Tesseract's hardcoded registry path
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
TESSDATA_DIR = os.environ.get(
    "TESSDATA_PREFIX",
    os.path.join(_APP_DIR, "tessdata")
)
os.environ['TESSDATA_PREFIX'] = TESSDATA_DIR

# Units of measure — OCR may mangle them
_JM_PAT = r'(?:KOM|kom|L|l|lit|SET|set|PAR|par|PAK|pak|M|m|tL)'


def _parse_number(s):
    """Parse Serbian number format: 1.492,00 -> 1492.00
    
    Handles OCR artifacts:
      - 1.26820  -> 1268.20 (dot used wrong, no comma)
      - 498.18   -> 498.18  (dot as decimal, no thousands)
      - 67200    -> 672.00  (missing comma entirely)
      - 463.68,  -> 463.68  (trailing comma)
      - 1.492,00 -> 1492.00 (correct Serbian format)
    """
    # Strip everything except digits, dots, commas
    s = re.sub(r'[^\d.,]', '', s)
    s = s.strip(' .,')
    if not s:
        return 0.0
    
    has_comma = ',' in s
    has_dot = '.' in s
    
    if has_comma and has_dot:
        # Serbian: 1.492,00 — dots are thousands, comma is decimal
        s = s.replace('.', '').replace(',', '.')
    elif has_comma and not has_dot:
        # 722,00 or 511,29 — comma is decimal
        s = s.replace(',', '.')
    elif has_dot and not has_comma:
        # Could be: 498.18 (decimal) or 1.26820 (mangled)
        parts = s.split('.')
        if len(parts) == 2:
            if len(parts[1]) == 2:
                # 498.18 — dot is decimal, looks correct
                pass  # keep as is
            elif len(parts[1]) > 2:
                # 1.26820 — mangled, remove dot and insert decimal before last 2
                raw = s.replace('.', '')
                s = raw[:-2] + '.' + raw[-2:]
            else:
                # 3.8 — dot is decimal
                pass
        else:
            # Multiple dots: 3.804.60 — remove all, insert decimal
            raw = s.replace('.', '')
            s = raw[:-2] + '.' + raw[-2:]
    else:
        # No comma, no dot: 67200 — insert decimal before last 2 if > 4 chars
        if len(s) > 4:
            s = s[:-2] + '.' + s[-2:]
    
    try:
        return float(s)
    except ValueError:
        return 0.0


def _extract_parts_line(line):
    """Try to extract a part from an invoice line.
    
    OCR produces messy output like:
      4 10921639-SL MOTORNO ULJE WR SW0 1L swao tL 3 KOM ¬1.492,00 1.26820 -3.804,60
      4 OPS45I2 FILTER ULJA 4854 4820 1 KOM = 741,00 511,29 511,29
    
    Strategy: find 'N KOM' (or other JM) in the line, then:
      - Everything before qty+JM contains RB + catalog + name + control numbers
      - Everything after qty+JM contains prices (with possible OCR junk)
    """
    # Find quantity + unit pattern: "3 KOM" or "1 KOM"
    jm_match = re.search(r'(\d+)\.?\s+' + _JM_PAT + r'\s+', line, re.IGNORECASE)
    if not jm_match:
        return None
    
    qty = int(jm_match.group(1))
    before = line[:jm_match.start()].strip()
    after = line[jm_match.end():].strip()
    
    # BEFORE: "4 10921639-SL MOTORNO ULJE WR SW0 1L swao"
    # Remove leading RB number
    before = re.sub(r'^\d+\s+', '', before)
    # Remove catalog number (usually has digits+letters+hyphens)
    before = re.sub(r'^\S*\d+\S*\s+', '', before, count=1)
    # The rest is the part name + possible trailing control numbers
    name = before.strip()
    # Remove trailing control numbers (sequences of 3+ digits possibly with spaces)
    name = re.sub(r'\s+\d[\d\s]{3,}$', '', name)
    # Remove trailing lowercase OCR garbage (but keep uppercase words like ULJA)
    # E.g. "MOTORNO ULJE WR SW0 1L swao tL" -> remove "swao tL"
    name = re.sub(r'(\s+[a-z]\w*)+\s*$', '', name)
    # Remove common OCR junk chars
    name = re.sub(r'[¬=|]', '', name).strip()
    
    if not name:
        name = ""
    
    # AFTER: "¬1.492,00 1.26820 -3.804,60" or "722,00 498.18 498,18"
    # Extract all number-like tokens (strip OCR junk around them)
    price_tokens = re.findall(r'[\d.,]{3,}', after)
    
    if len(price_tokens) >= 3:
        price = _parse_number(price_tokens[0])
        price_disc = _parse_number(price_tokens[1])
    elif len(price_tokens) == 2:
        price = _parse_number(price_tokens[0])
        price_disc = _parse_number(price_tokens[1])
    elif len(price_tokens) == 1:
        price = _parse_number(price_tokens[0])
        price_disc = price
    else:
        return None
    
    if price <= 0 and price_disc <= 0:
        return None
    
    return {
        'name': name,
        'qty': qty,
        'price': price,
        'price_disc': price_disc
    }


def _ocr_image(img):
    """Run Tesseract OCR on a PIL Image, return text.
    
    Uses subprocess with stdin/stdout pipe to avoid temp file issues.
    Passes --tessdata-dir and TESSDATA_PREFIX env var explicitly.
    """
    import subprocess
    
    # Convert image to PNG bytes for stdin
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    png_bytes = buf.getvalue()
    
    cmd = [
        TESSERACT_CMD,
        'stdin', 'stdout',
        '--tessdata-dir', TESSDATA_DIR,
        '-l', 'eng',
    ]
    
    env = os.environ.copy()
    env['TESSDATA_PREFIX'] = TESSDATA_DIR
    
    log.info("Running: %s", ' '.join(cmd))
    
    result = subprocess.run(
        cmd, input=png_bytes, capture_output=True, timeout=60, env=env
    )
    
    if result.returncode != 0:
        stderr = result.stderr.decode('utf-8', errors='replace')
        log.error("Tesseract stderr: %s", stderr)
        raise RuntimeError(f"Tesseract error: {stderr}")
    
    return result.stdout.decode('utf-8', errors='replace')


def _pdf_to_images(file_bytes):
    """Convert PDF bytes to list of PIL Images (300 DPI)."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(file_bytes)
    images = []
    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=300 / 72)
        images.append(bitmap.to_pil())
    pdf.close()
    return images


def parse_invoice(file_storage):
    """Parse an uploaded invoice file and extract parts.

    Args:
        file_storage: A werkzeug FileStorage object (from request.files)

    Returns:
        list of dicts: [{"name": str, "qty": int, "price": float, "price_disc": float}, ...]
    """
    filename = file_storage.filename.lower()
    file_bytes = file_storage.read()

    # Get images from file
    if filename.endswith('.pdf'):
        images = _pdf_to_images(file_bytes)
    else:
        images = [Image.open(io.BytesIO(file_bytes))]

    # OCR all pages
    all_text = []
    for img in images:
        text = _ocr_image(img)
        all_text.append(text)
        log.debug("OCR page text:\n%s", text[:2000])

    # Parse each page separately, then merge
    page_results = []
    for page_text in all_text:
        lines = page_text.split('\n')
        page_parts = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            result = _extract_parts_line(line)
            if not result:
                continue

            # If name is too short or missing, look back at previous lines
            if len(result['name']) < 3:
                for back in range(1, 5):
                    if i - back < 0:
                        break
                    prev = lines[i - back].strip()
                    if not prev:
                        continue
                    if re.search(_JM_PAT, prev, re.IGNORECASE):
                        continue
                    candidate = re.sub(r'^\d+\s+', '', prev)
                    candidate = re.sub(r'^\S*\d+\S*\s+', '', candidate, count=1)
                    candidate = candidate.strip()
                    candidate = re.sub(r'\s+\d[\d\s]{3,}$', '', candidate)
                    candidate = re.sub(r'(\s+[a-z]\w*)+\s*$', '', candidate)
                    candidate = re.sub(r'[\xac=|]', '', candidate).strip()
                    # Skip table headers
                    skip = ('opis', 'naziv', 'artikal', 'rb',
                            'kataloski', 'jedinicna', 'jedinicna cena',
                            'kolicina', 'iznos', 'popust', 'cena',
                            'prod', 'prod.', 'ukupno')
                    if candidate.lower().strip() in skip:
                        continue
                    if len(candidate) >= 3 and any(c.isalpha() for c in candidate):
                        result['name'] = candidate
                        break

            if result['name'] and len(result['name']) >= 3:
                page_parts.append(result)

        page_results.append(page_parts)

    # Collect ALL raw matches (including nameless ones) per page
    raw_pages = []
    for page_text in all_text:
        plines = page_text.split('\n')
        raw = []
        for line in plines:
            line = line.strip()
            if not line:
                continue
            r = _extract_parts_line(line)
            if r:
                raw.append(r)
        raw_pages.append(raw)

    # Find the page with the best names and the page with discounts
    def named_count(pp):
        return sum(1 for p in pp if len(p.get('name', '')) >= 3)

    def has_disc(pp):
        return any(p['price'] != p['price_disc'] for p in pp)

    all_pages = [(i, pp) for i, pp in enumerate(raw_pages) if pp]
    if not all_pages:
        return []

    # Sort by count descending
    all_pages.sort(key=lambda x: len(x[1]), reverse=True)

    best_named = max(all_pages, key=lambda x: named_count(x[1]))
    disc_list = [x for x in all_pages if has_disc(x[1])]

    if disc_list and best_named:
        dp = max(disc_list, key=lambda x: len(x[1]))[1]
        np_ = best_named[1]

        # Match by position — use names from named page, prices from disc page
        best = []
        for i in range(max(len(dp), len(np_))):
            name = np_[i]['name'] if i < len(np_) and len(np_[i].get('name', '')) >= 3 else ''
            if i < len(dp):
                price = dp[i]['price']
                price_disc = dp[i]['price_disc']
                qty = dp[i]['qty']
            elif i < len(np_):
                price = np_[i]['price']
                price_disc = np_[i]['price_disc']
                qty = np_[i]['qty']
            else:
                continue
            if not name and i < len(dp):
                name = dp[i].get('name', '')
            if name and len(name) >= 3:
                best.append({'name': name, 'qty': qty, 'price': price, 'price_disc': price_disc})
    else:
        best = all_pages[0][1]

    # Deduplicate by name, filter short names
    parts = []
    seen = set()
    for p in best:
        if len(p.get('name', '')) >= 3 and p['name'] not in seen:
            parts.append(p)
            seen.add(p['name'])

    log.info("Parsed %d parts from invoice", len(parts))
    return parts
