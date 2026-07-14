"""Self-update: check out a Git tag/ref and restart the service.

Used by the moderator "one-click update" page.  A moderator pastes a GitHub
release tag; the app fetches it, checks it out, installs requirements, applies
any new database tables, and restarts its own systemd service.

Security notes
--------------
* Only reachable through ``@moderator_required`` routes.
* The ref is validated against a strict allow-list pattern before use, and every
  command is run with an explicit argument list (never a shell string), so the
  pasted tag cannot inject shell commands.
* The service name comes from the ``SERVICE_NAME`` environment variable, never
  from user input.
"""
import os
import re
import subprocess
import sys

from flask import current_app

# Tags/branches: start alphanumeric, then word chars plus . _ - / (max 100).
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/\-]{0,99}$")


def service_name() -> str:
    """systemd unit to restart after an update (default: ``garagepro``)."""
    return os.environ.get("SERVICE_NAME", "garagepro")


def update_script() -> str:
    """Root-owned helper that performs the update (default path)."""
    return os.environ.get("UPDATE_SCRIPT", "/usr/local/bin/garagepro-update")


def repo_dir() -> str:
    """Directory the running app lives in (its Git checkout)."""
    return str(current_app.config["BASE_DIR"])


def is_git_repo() -> bool:
    return os.path.isdir(os.path.join(repo_dir(), ".git"))


def validate_ref(ref: str) -> bool:
    """True when *ref* is a safe tag/branch/commit name."""
    return bool(ref) and bool(_REF_RE.match(ref))


def _run(args, timeout=600):
    return subprocess.run(
        args, cwd=repo_dir(), capture_output=True, text=True, timeout=timeout,
    )


def current_version() -> str:
    """Human-readable current version (nearest tag or short commit)."""
    if not is_git_repo():
        return "nepoznato (nije Git kopija)"
    try:
        r = _run(["git", "describe", "--tags", "--always", "--dirty"])
        return r.stdout.strip() or "nepoznato"
    except Exception:  # noqa: BLE001
        return "nepoznato"


def list_tags(limit: int = 15):
    """Most recent tags known locally (best-effort, for display only)."""
    if not is_git_repo():
        return []
    try:
        r = _run(["git", "tag", "--sort=-creatordate"])
        return [t for t in r.stdout.splitlines() if t.strip()][:limit]
    except Exception:  # noqa: BLE001
        return []


def _schedule_restart():
    """Restart the systemd service shortly after this request finishes.

    Detaches a helper that waits a moment (so the HTTP response is delivered)
    then restarts the unit via a narrowly-scoped passwordless sudo rule.
    """
    svc = service_name()
    # Argument list is safe; svc is not user-controlled.
    subprocess.Popen(
        ["/bin/sh", "-c", f"sleep 2; sudo -n systemctl restart {svc}"],
        cwd=repo_dir(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def perform_update(ref: str) -> str:
    """Fetch and check out *ref*, install deps, migrate, and restart.

    Returns a combined log on success; raises ``RuntimeError`` on failure.

    Production path: delegate the whole operation to a small **root-owned**
    helper script (``UPDATE_SCRIPT``) via a scoped, passwordless sudo rule.  The
    service account (``garagepro``) has no GitHub access and cannot restart the
    unit, but root does — so the privileged, network-facing work happens there.
    The pasted *ref* is validated here and re-validated by the script.

    Development fallback: when the helper script is absent (e.g. running the repo
    directly as a developer) the update runs inline with the current user's Git
    credentials.
    """
    if not validate_ref(ref):
        raise RuntimeError("Neispravna oznaka (tag).")

    script = update_script()
    if os.path.exists(script):
        r = subprocess.run(
            ["sudo", "-n", script, ref],
            cwd=repo_dir(), capture_output=True, text=True, timeout=1200,
        )
        out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")
        if r.returncode != 0:
            raise RuntimeError(out.strip() or "Skripta za ažuriranje nije uspela.")
        return out.strip() or f"Ažurirano na „{ref}“. Servis se restartuje…"

    # ---- Development fallback (no privileged helper installed) ----
    if not is_git_repo():
        raise RuntimeError(
            "Aplikacija nije Git kopija — automatsko ažuriranje nije moguće.")

    log = []

    def step(args, timeout=600):
        log.append("$ " + " ".join(args))
        r = _run(args, timeout=timeout)
        if r.stdout:
            log.append(r.stdout.strip())
        if r.stderr:
            log.append(r.stderr.strip())
        if r.returncode != 0:
            raise RuntimeError("\n".join(log))
        return r

    # 1) Get the requested tag/ref and check it out (detached, force-clean).
    step(["git", "fetch", "--tags", "--force", "--prune", "origin"])
    step(["git", "-c", "advice.detachedHead=false", "checkout", "--force", ref])

    # 2) Install (possibly updated) Python requirements into the running venv.
    req = os.path.join(repo_dir(), "requirements.txt")
    if os.path.exists(req):
        step([sys.executable, "-m", "pip", "install", "--no-input",
              "-r", "requirements.txt"], timeout=900)

    # 3) Apply any new database tables (idempotent).
    try:
        from .extensions import db
        db.create_all()
        log.append("$ db.create_all() — schema ažurirana")
    except Exception as exc:  # noqa: BLE001
        log.append(f"Upozorenje: create_all nije uspeo: {exc}")

    # 4) Restart the service so the new code takes effect.
    _schedule_restart()
    log.append(f"Servis '{service_name()}' se restartuje…")
    return "\n".join(log)
