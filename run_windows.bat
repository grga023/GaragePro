@echo off
REM ============================================================
REM  Auto Servis - pokretanje na Windowsu (za testiranje)
REM ============================================================
cd /d "%~dp0"

if not exist ".venv" (
    echo [*] Kreiram virtuelno okruzenje...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [*] Instaliram zavisnosti...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt

if not exist "instance\carservice.db" (
    echo [*] Kreiram bazu sa demo podacima...
    python init_db.py --demo
)

echo.
echo ============================================================
echo  Aplikacija je pokrenuta na:  http://127.0.0.1:8000
echo  Admin  -^>  admin  / admin123
echo  Radnik -^>  radnik / radnik123
echo  (Ctrl+C za prekid)
echo ============================================================
echo.
python serve.py
