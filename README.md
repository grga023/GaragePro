# Auto Servis — veb aplikacija za automehaničarski servis

Laka veb aplikacija (Python + Flask + SQLite) za vođenje automehaničarskog
servisa. Napravljena da radi i na **Raspberry Pi Zero 2W** (bez Docker-a, kao
systemd servis) i na **Windows-u** (za testiranje).

Jezik interfejsa: **srpski (latinica)**.

---

## Mogućnosti (pregled zahteva)

- **Dva tipa naloga:** administrator i radnik (prijava + registracija). Prvi
  registrovani nalog automatski postaje administrator.
  - Administrator vidi **sve** servise i cene; radnik vidi **samo svoje**.
  - I administrator i radnik su radnici u servisu.
- **Vozila** se vode po registarskoj oznaci: vlasnik, kilometraža, telefon,
  slika, marka/model/motor/gorivo/godište (npr. „BMW 320 2.0 dizel 2020“).
- **Servis** sadrži: tabelu ugrađenih delova (naziv, cena bez popusta, cena sa
  popustom, količina), cenu i opis rada, datum, ukupnu cenu i profit.
- **Tok „prvo registracija“:** na početku servisa unosite registarsku oznaku —
  ako vozilo postoji, odmah dodajete servis; ako ne postoji, prvo ga
  registrujete.
- **Kilometraža** se ažurira na svakom servisu (poslednja poznata na vozilu).
- **Štampa** (otvara dijalog pregledača):
  - *za kupca* — bez cene rada, delovi po ceni bez popusta;
  - *za vlasnika* — sa radom, obe cene delova (sa i bez popusta) i profitom.
  - Moguće štampanje **jednog servisa** ili **svih servisa jednog vozila**
    (svaki sa svojim datumom i tabelom delova).
  - Zaglavlje: logo (gore levo, ~4×2 cm), naziv/adresa/kontakt servisa (gore
    desno), zatim podaci o vozilu (podaci podebljani) i poslednja kilometraža.
- **Žurnali:** dnevni / nedeljni / mesečni, po radniku i zbirno; slanje na
  e-mail (radnik dobija svoj, zbirni ide samo administratoru).
- **Analitika:** analiza profita i cena delova (sa popustom i bez).
- **Podešavanje servisa:** naziv, adresa, kontakt i logo (unosi administrator).

---

## Preduslov

- **Python 3.10+** (preporučeno 3.11 ili 3.12)
- **Tesseract OCR** (opcionalno — potreban samo za OCR parsiranje faktura).
  Prepoznavanje je na **srpskom (latinica)** — model `srp_latn` je uključen u
  `app/tessdata/`, pa je dovoljno instalirati samu Tesseract aplikaciju.
  PDF fakture zahtevaju `pypdfium2` (instalira se preko `requirements.txt`).

---

## Instalacija na PC (Windows)

### Opcija A — automatski (preporučeno)

Dvoklik na **`run_windows.bat`** — skripta sama kreira virtualno okruženje,
instalira zavisnosti, ubacuje demo podatke i pokreće server.

### Opcija B — ručno

1. **Kloniranje / preuzimanje projekta:**

   ```powershell
   git clone <repo-url>  D:\GaragePro
   cd D:\GaragePro
   ```

2. **Kreiranje virtualnog okruženja i instalacija zavisnosti:**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Konfiguracija (opcionalno):**

   ```powershell
   copy .env.example .env
   notepad .env                # podesite SECRET_KEY, SMTP, PORT…
   ```

   > Ako preskočite ovaj korak, aplikacija radi sa podrazumevanim podešavanjima
   > (port 8000, valuta RSD, bez SMTP-a).

4. **Inicijalizacija baze podataka:**

   ```powershell
   python init_db.py --demo      # kreira tabele + demo podatke
   # ili:
   python init_db.py             # prazna baza (prvi nalog = administrator)
   ```

5. **Pokretanje servera:**

   ```powershell
   python serve.py               # produkcioni (Waitress) — http://127.0.0.1:8000
   # ili:
   python run.py                 # debug režim (auto-reload)
   ```

6. Otvorite **<http://127.0.0.1:8000>** u pregledaču.

### Demo nalozi

| Uloga         | Korisnik | Lozinka     |
|---------------|----------|-------------|
| Administrator | `admin`  | `admin123`  |
| Radnik        | `radnik` | `radnik123` |

> Bez `--demo` baza je prazna — prvi nalog koji registrujete automatski postaje
> administrator.

---

## Instalacija na Raspberry Pi (3B+ / 4B / 5 / Zero 2W)

### Opcija A — jednom komandom (preporučeno)

Instaler u `deploy/` radi sve automatski: sistemske pakete, korisnika, venv,
bazu, systemd servis, zram swap (ako je RAM ≤ 1 GB) i dnevni backup.

```bash
# 1. Preuzmite projekat na Pi:
git clone <repo-url>  ~/garagepro
cd ~/garagepro

# 2. Preimenujte i pokrenite instaler:
mv deploy/install-garagepro.txt deploy/install-garagepro.sh
chmod +x deploy/install-garagepro.sh
sudo bash deploy/install-garagepro.sh
```

Po završetku, aplikacija je dostupna na **`http://<IP-adresa-Pi>:8000`**.

### Opcija B — ručno, korak po korak

1. **Sistemske zavisnosti:**

   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip python3-dev \
       tesseract-ocr tesseract-ocr-srp libjpeg-dev libopenjp2-7 \
       libffi-dev zlib1g-dev libfreetype6-dev sqlite3
   ```

2. **Preuzimanje projekta:**

   ```bash
   git clone <repo-url>  ~/garagepro
   cd ~/garagepro
   ```

3. **Virtualno okruženje:**

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install --upgrade pip
   .venv/bin/pip install -r requirements.txt
   ```

4. **Konfiguracija:**

   ```bash
   cp .env.example .env
   nano .env                    # podesite SECRET_KEY, SMTP, ENABLE_SCHEDULER…
   ```

   > Za automatske žurnale (dnevni u 20:00, nedeljni nedeljom, mesečni poslednjeg
   > dana) postavite `ENABLE_SCHEDULER=true`.

5. **Inicijalizacija baze:**

   ```bash
   .venv/bin/python init_db.py --demo      # ili bez --demo za praznu bazu
   ```

6. **Pokretanje (ručno, za test):**

   ```bash
   .venv/bin/python serve.py
   ```

7. **Instalacija kao systemd servis (autostart + restart):**

   ```bash
   # Kopirajte priloženi fajl:
   sudo cp deploy/garagepro-service.txt /etc/systemd/system/garagepro.service

   sudo systemctl daemon-reload
   sudo systemctl enable --now garagepro
   ```

   Korisne komande:

   ```bash
   sudo systemctl status garagepro       # provera statusa
   sudo systemctl restart garagepro      # restart
   sudo journalctl -u garagepro -f       # logovi u realnom vremenu
   ```

### Deinstalacija

```bash
mv deploy/uninstall-garagepro.txt deploy/uninstall-garagepro.sh
chmod +x deploy/uninstall-garagepro.sh
sudo bash deploy/uninstall-garagepro.sh
```

---

## Konfiguracija (`.env`)

Kopirajte `.env.example` u `.env` i podesite vrednosti. Podrazumevane vrednosti
rade bez izmena za lokalno testiranje.

| Promenljiva         | Podrazumevano              | Opis                                      |
|---------------------|----------------------------|--------------------------------------------|
| `SECRET_KEY`        | `promeni-me-u-produkciji`  | Tajni ključ (obavezno promeniti u produkciji) |
| `PORT`              | `8000`                     | Port servera                               |
| `CURRENCY`          | `RSD`                      | Valuta za prikaz cena                      |
| `ENABLE_SCHEDULER`  | `false`                    | Automatsko slanje žurnala                  |
| `SMTP_HOST`         | *(prazno)*                 | SMTP server za e-mail žurnale              |
| `SMTP_PORT`         | `587`                      | SMTP port                                  |
| `SMTP_USER`         | *(prazno)*                 | SMTP korisnik                              |
| `SMTP_PASSWORD`     | *(prazno)*                 | SMTP lozinka                               |
| `ADMIN_EMAIL`       | *(prazno)*                 | E-mail administratora (zbirni žurnali)     |
| `BACKUP_KEEP`       | `14`                       | Koliko backup fajlova čuvati               |
| `SECURE_COOKIES`    | `false`                    | `true` ako koristite HTTPS                 |
| `TRUST_PROXY`       | `false`                    | `true` ako ste iza nginx reverse proxy-ja  |

---

## Struktura projekta

```
app/
  __init__.py      app factory, rute za medije, error handleri
  config.py        konfiguracija (env / .env)
  models.py        User, Company, Car, Service, Part
  auth.py          prijava, registracija, upravljanje korisnicima
  main.py          početna + podešavanje servisa
  cars.py          registracija/izmena vozila
  services.py      tok servisa (prvo registracija), delovi, rad
  reports.py       žurnali + analitika
  printing.py      štampa (kupac / vlasnik)
  email_utils.py   slanje e-maila (SMTP)
  scheduler.py     automatski žurnali (APScheduler)
  utils.py         formatiranje (valuta/datum), slike, periodi
  templates/…      Jinja2 šabloni (srpski, latinica)
  static/…         Bootstrap + stil + JS
init_db.py         kreiranje šeme / demo podaci
run.py             razvojni server (debug)
serve.py           produkcioni server (Waitress)
deploy/carservice.service   systemd jedinica za Pi
run_windows.bat    pokretanje na Windows-u
```

---

## Model cena i profita

- Svaki deo ima **cenu bez popusta** (prodajna — plaća kupac) i **cenu sa
  popustom** (nabavna — trošak servisa).
- **Marža na delove** = prodajna − nabavna.
- **Profit servisa** = cena rada + marža na delove.
- **Ukupno za naplatu** = cena rada + delovi (prodajna).

Kupčev primerak prikazuje delove po prodajnoj ceni, bez rada i bez profita.
Vlasnički primerak prikazuje sve.
