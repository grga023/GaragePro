#!/usr/bin/env bash
# ============================================================================
#  Auto Servis - instalacija na Raspberry Pi (Raspberry Pi OS / Debian)
#  Pokretanje:  bash deploy/install_pi.sh
# ============================================================================
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_USER="${SUDO_USER:-$(whoami)}"

echo ">> Aplikacija: $APP_DIR"
echo ">> Korisnik:   $SERVICE_USER"

echo ">> Instaliram sistemske pakete..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip libjpeg-dev zlib1g-dev

echo ">> Kreiram virtuelno okruženje i instaliram zavisnosti..."
cd "$APP_DIR"
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
  echo ">> Kreiram .env (izmenite SECRET_KEY i SMTP podatke!)"
  cp .env.example .env
  # nasumičan SECRET_KEY
  RK="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${RK}/" .env
fi

echo ">> Inicijalizujem bazu (ako ne postoji)..."
if [ ! -f instance/carservice.db ]; then
  ./.venv/bin/python init_db.py
  echo "   Baza je prazna — prvi registrovani nalog postaje administrator."
fi

echo ">> Postavljam systemd servise..."
render() {
  sed -e "s#/home/pi/carservice#$APP_DIR#g" \
      -e "s/^User=pi/User=$SERVICE_USER/" \
      -e "s/^Group=pi/Group=$SERVICE_USER/" "$1"
}

render deploy/carservice.service        | sudo tee /etc/systemd/system/carservice.service        >/dev/null
render deploy/carservice-backup.service | sudo tee /etc/systemd/system/carservice-backup.service >/dev/null
sudo cp deploy/carservice-backup.timer    /etc/systemd/system/carservice-backup.timer

sudo systemctl daemon-reload
sudo systemctl enable --now carservice.service
sudo systemctl enable --now carservice-backup.timer

IP="$(hostname -I | awk '{print $1}')"
echo ""
echo "============================================================"
echo " Gotovo! Aplikacija radi na:  http://${IP}:8000"
echo " Status:   sudo systemctl status carservice"
echo " Dnevnik:  journalctl -u carservice -f"
echo "============================================================"
