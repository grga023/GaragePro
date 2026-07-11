"""Invoice-OCR regression check.

Runs the invoice parser against every fixture listed in ``expected.json`` (in
this folder) and reports pass/fail.  Framework-free — just run it:

    python resources/test_invoices/check_invoices.py

To add a new sample: drop the image next to this file and add an entry to
``expected.json``:

    "myinvoice.jpg": {
        "count": 1,
        "parts": [
            {"name_contains": "ZGLOB", "qty": 1, "price": 4380.0, "price_disc": 3109.8}
        ]
    }

Each expected part supports: name_contains (case-insensitive substring), qty,
price, price_disc.  Requires Tesseract to be installed (see README).
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.invoice_parser import parse_invoice, TESSERACT_CMD  # noqa: E402


class _FileWrapper:
    def __init__(self, name, data):
        self.filename = name
        self._data = data

    def read(self):
        return self._data


def _check_part(actual, expected):
    errs = []
    want = expected.get("name_contains")
    if want and want.lower() not in actual["name"].lower():
        errs.append(f"name '{actual['name']}' missing '{want}'")
    for key in ("qty", "price", "price_disc"):
        if key in expected and actual[key] != expected[key]:
            errs.append(f"{key} {actual[key]} != {expected[key]}")
    return errs


def main():
    if not (TESSERACT_CMD and os.path.exists(TESSERACT_CMD)):
        print(f"SKIP: Tesseract not found at {TESSERACT_CMD}")
        return 0

    with open(os.path.join(HERE, "expected.json"), encoding="utf-8") as fh:
        cases = json.load(fh)

    failures = 0
    for fname, spec in cases.items():
        path = os.path.join(HERE, fname)
        if not os.path.exists(path):
            print(f"FAIL {fname}: fixture file missing")
            failures += 1
            continue
        with open(path, "rb") as fh:
            parts = parse_invoice(_FileWrapper(fname, fh.read()))

        problems = []
        if "count" in spec and len(parts) != spec["count"]:
            problems.append(f"count {len(parts)} != {spec['count']}")
        for i, exp in enumerate(spec.get("parts", [])):
            if i >= len(parts):
                problems.append(f"part[{i}] missing")
                continue
            problems += [f"part[{i}]: {e}" for e in _check_part(parts[i], exp)]

        if problems:
            failures += 1
            print(f"FAIL {fname}:")
            for p in problems:
                print(f"       - {p}")
            for p in parts:
                print(f"       got: {p}")
        else:
            print(f"PASS {fname}: {len(parts)} part(s) -> "
                  + "; ".join(p["name"] for p in parts))

    print(f"\n{len(cases) - failures}/{len(cases)} invoice checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
