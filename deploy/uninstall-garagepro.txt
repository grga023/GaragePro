#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════
#  GaragePro — Uninstaller
# ══════════════════════════════════════════════════════════════════
#
#  Usage:
#      mv deploy/uninstall-garagepro.txt deploy/uninstall-garagepro.sh
#      sudo bash deploy/uninstall-garagepro.sh
#
#  Removes the systemd service, cron job, system user, and
#  optionally the application data at /opt/garagepro.
# ══════════════════════════════════════════════════════════════════

set -euo pipefail

APP_NAME="garagepro"
APP_DIR="/opt/${APP_NAME}"
APP_USER="garagepro"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
fail()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo -e "${RED}╔══════════════════════════════════════════════╗${NC}"
echo -e "${RED}║        🔧  GaragePro  Uninstaller            ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════╝${NC}"
echo ""

if [[ $EUID -ne 0 ]]; then
    fail "This script must be run as root (use sudo)."
fi

# ── Stop and remove service ─────────────────────────────────────
if systemctl is-active "$APP_NAME" &>/dev/null; then
    systemctl stop "$APP_NAME"
    info "Service stopped"
fi

if systemctl is-enabled "$APP_NAME" &>/dev/null; then
    systemctl disable "$APP_NAME"
    info "Service disabled"
fi

if [[ -f "/etc/systemd/system/${APP_NAME}.service" ]]; then
    rm -f "/etc/systemd/system/${APP_NAME}.service"
    systemctl daemon-reload
    info "Service file removed"
fi

# ── Remove zram swap if installed ───────────────────────────────
if [[ -f /etc/systemd/system/zram-swap.service ]]; then
    systemctl stop zram-swap 2>/dev/null || true
    systemctl disable zram-swap 2>/dev/null || true
    rm -f /etc/systemd/system/zram-swap.service
    systemctl daemon-reload
    info "zram swap service removed"
fi

# ── Remove cron job ─────────────────────────────────────────────
if [[ -f /etc/cron.d/garagepro-backup ]]; then
    rm -f /etc/cron.d/garagepro-backup
    info "Backup cron job removed"
fi

# ── Ask about data ──────────────────────────────────────────────
if [[ -d "$APP_DIR" ]]; then
    echo ""
    echo -e "${YELLOW}The application directory exists at ${APP_DIR}${NC}"
    echo -e "${YELLOW}This contains the database, uploads, and backups.${NC}"
    echo ""
    read -rp "Delete ALL application data? (y/N): " CONFIRM

    if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
        # Safety: backup the database first
        if [[ -f "$APP_DIR/instance/service.db" ]]; then
            BACKUP_PATH="/tmp/garagepro-final-backup-$(date +%Y%m%d_%H%M%S).db"
            cp "$APP_DIR/instance/service.db" "$BACKUP_PATH"
            info "Final database backup saved to: $BACKUP_PATH"
        fi
        rm -rf "$APP_DIR"
        info "Application directory removed"
    else
        warn "Keeping ${APP_DIR} — you can remove it manually later"
    fi
fi

# ── Remove system user ─────────────────────────────────────────
if id "$APP_USER" &>/dev/null; then
    userdel "$APP_USER" 2>/dev/null || true
    info "System user '${APP_USER}' removed"
fi

# ── Done ────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}GaragePro has been uninstalled.${NC}"
echo ""
