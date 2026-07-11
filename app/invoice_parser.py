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
import shutil
import logging

from PIL import Image, ImageOps, ImageFilter

log = logging.getLogger(__name__)

# Tesseract config — set env var BEFORE pytesseract is ever imported.
# Prefer the binary on PATH (Linux/macOS: /usr/bin/tesseract); fall back to the
# default Windows install location for local Windows testing.
TESSERACT_CMD = os.environ.get(
    "TESSERACT_CMD",
    shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
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

# Resampling filter constant (Pillow 10+ moved these under Image.Resampling)
_RESAMPLE = getattr(Image, "Resampling", Image).LANCZOS


# --------------------------------------------------------------------------
# Language selection + image preprocessing
# --------------------------------------------------------------------------
def _available_langs():
    """Set of Tesseract languages available in the local tessdata dir."""
    try:
        return {os.path.splitext(f)[0] for f in os.listdir(TESSDATA_DIR)
                if f.endswith('.traineddata')}
    except OSError:
        return set()


def _ocr_lang():
    """Prefer Serbian Latin (srp_latn); fall back to srp, then eng.

    English is appended so ASCII digits and currency codes stay accurate.
    """
    avail = _available_langs()
    if 'srp_latn' in avail:
        return 'srp_latn+eng' if 'eng' in avail else 'srp_latn'
    if 'srp' in avail:
        return 'srp+eng' if 'eng' in avail else 'srp'
    return 'eng'


def _preprocess(img, min_width=2200, max_scale=4.0):
    """Clean an invoice image for OCR (Pillow only — Raspberry-Pi friendly).

    Honour EXIF orientation, convert to grayscale, upscale small scans, then
    normalise contrast, denoise and sharpen.  Returns a grayscale image and
    lets Tesseract do its own (Otsu) binarisation, which copes with uneven
    lighting better than a single global threshold.
    """
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:  # noqa: BLE001 - malformed EXIF must not break OCR
        pass
    img = img.convert('L')
    if img.width and img.width < min_width:
        scale = min(min_width / img.width, max_scale)
        img = img.resize((int(img.width * scale), int(img.height * scale)),
                         _RESAMPLE)
    img = ImageOps.autocontrast(img, cutoff=1)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=150, threshold=3))
    return img


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


def _run_tesseract(img, mode='txt'):
    """Run Tesseract on a PIL image and return decoded stdout.

    mode: 'txt' for plain text, 'tsv' for tab-separated word boxes.
    Tuned for invoices: Serbian-Latin (+eng), LSTM engine, uniform block,
    preserved inter-word spacing so columns stay aligned.
    """
    import subprocess

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    png_bytes = buf.getvalue()

    cmd = [
        TESSERACT_CMD, 'stdin', 'stdout',
        '--tessdata-dir', TESSDATA_DIR,
        '-l', _ocr_lang(),
        '--oem', '1', '--psm', '6', '--dpi', '300',
        '-c', 'preserve_interword_spaces=1',
        mode,
    ]

    env = os.environ.copy()
    env['TESSDATA_PREFIX'] = TESSDATA_DIR

    log.info("Running: %s", ' '.join(cmd))

    result = subprocess.run(
        cmd, input=png_bytes, capture_output=True, timeout=120, env=env
    )

    if result.returncode != 0:
        stderr = result.stderr.decode('utf-8', errors='replace')
        log.error("Tesseract stderr: %s", stderr)
        raise RuntimeError(f"Tesseract error: {stderr}")

    return result.stdout.decode('utf-8', errors='replace')


def _ocr_image(img):
    """Plain-text OCR (used for name back-fill and as a fallback)."""
    return _run_tesseract(img, 'txt')


def _ocr_tsv(img):
    """Word-level OCR with layout (TSV)."""
    return _run_tesseract(img, 'tsv')


def _tsv_rows(tsv_text, min_conf=35):
    """Group TSV words into visual rows (ordered top->bottom, left->right).

    Drops low-confidence words.  Returns a list of rows; each row is a list of
    {'text', 'left', 'top', 'conf'} dicts.
    """
    rows = {}
    for ln in tsv_text.splitlines():
        cols = ln.split('\t')
        if len(cols) < 12 or cols[0] != '5':  # level 5 == word
            continue
        try:
            conf = float(cols[10])
        except ValueError:
            continue
        text = cols[11].strip()
        if not text or conf < min_conf:
            continue
        key = (cols[2], cols[3], cols[4])  # block, paragraph, line
        rows.setdefault(key, []).append({
            'text': text, 'left': int(cols[6]), 'top': int(cols[7]), 'conf': conf,
        })
    ordered = []
    for words in rows.values():
        words.sort(key=lambda w: w['left'])
        ordered.append((min(w['top'] for w in words), words))
    ordered.sort(key=lambda t: t[0])
    return [w for _, w in ordered]


def _row_text(words):
    return ' '.join(w['text'] for w in words)


def _clean_name_tokens(tokens):
    """Keep only description ("Opis") words, dropping the RB index, catalog and
    control numbers, and left-margin OCR noise."""
    words = []
    for t in tokens:
        tok = t.strip('“”„"\'`.,:;|=\xac*()[]{}<>')
        if not tok:
            continue
        letters = sum(c.isalpha() for c in tok)
        digits = sum(c.isdigit() for c in tok)
        if letters == 0:
            continue  # pure numbers (RB, control no.) or punctuation
        if digits >= 4 or ('-' in tok and digits >= 2):
            continue  # catalog number, e.g. 644009-GSP / 10921639-SL / OPS4512
        if letters == 1 and len(tok) <= 2:
            continue  # single-letter margin junk (A, S, ...)
        words.append(tok)
    return words


def _extract_from_words(words):
    """Column/token based extraction from one TSV row.

    Uses Tesseract's word segmentation (positions) instead of regex-splitting a
    flat string: find 'qty JM', keep the description words before it as the name
    (dropping RB / catalog / control numbers), and read the numeric words after
    it as the prices.
    """
    texts = [w['text'] for w in words]
    jm_idx = None
    qty = 1
    for i in range(1, len(texts)):
        if re.fullmatch(_JM_PAT, texts[i], re.IGNORECASE) and \
                re.fullmatch(r'\d+\.?', texts[i - 1]):
            jm_idx = i
            qty = int(re.sub(r'\D', '', texts[i - 1]) or '1')
            break
    if jm_idx is None:
        return None

    before = texts[:jm_idx - 1]
    after = texts[jm_idx + 1:]
    name = ' '.join(_clean_name_tokens(before))

    # Numeric price tokens after the unit of measure.
    nums = [_parse_number(t) for t in after if re.search(r'\d', t)]
    nums = [n for n in nums if n > 0]
    if not nums:
        return None
    price = nums[0]
    price_disc = nums[1] if len(nums) > 1 else nums[0]

    return {'name': name, 'qty': qty, 'price': price, 'price_disc': price_disc}


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

    # Preprocess + OCR every page: TSV for the parts table, plain text for the
    # name back-fill fallback.
    all_text = []
    all_rows = []
    for img in images:
        proc = _preprocess(img)
        all_text.append(_ocr_image(proc))
        all_rows.append(_tsv_rows(_ocr_tsv(proc)))
        log.debug("OCR page rows: %d", len(all_rows[-1]))

    # Build parts per page from TSV word-rows (token/column based), falling back
    # to the flat-line regex parser for any row it can't split.  Back-fill a
    # missing name from a nearby description row.
    header_skip = ('opis', 'naziv', 'artikal', 'rb', 'kataloski', 'jedinicna',
                   'jedinicna cena', 'kolicina', 'iznos', 'popust', 'cena',
                   'prod', 'prod.', 'ukupno')
    raw_pages = []
    for rows in all_rows:
        row_texts = [_row_text(r) for r in rows]
        raw = []
        for i, words in enumerate(rows):
            r = _extract_from_words(words)
            if not r:
                r = _extract_parts_line(row_texts[i])
            if not r:
                continue
            if len(r['name']) < 3:
                for back in range(1, 5):
                    if i - back < 0:
                        break
                    prev = row_texts[i - back].strip()
                    if not prev or re.search(_JM_PAT, prev, re.IGNORECASE):
                        continue
                    cand = re.sub(r'^\d+\s+', '', prev)
                    cand = re.sub(r'^\S*\d+\S*\s+', '', cand, count=1)
                    cand = re.sub(r'\s+\d[\d\s]{3,}$', '', cand.strip())
                    cand = re.sub(r'[\xac=|]', '', cand).strip()
                    if cand.lower() in header_skip:
                        continue
                    if len(cand) >= 3 and any(c.isalpha() for c in cand):
                        r['name'] = cand
                        break
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
